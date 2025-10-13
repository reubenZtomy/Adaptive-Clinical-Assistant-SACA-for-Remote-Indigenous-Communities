
# arrernte_audio_scraper.py (robust + deduped output)
import argparse
import csv
import json
import time
import unicodedata
from contextlib import contextmanager
from typing import List, Set, Tuple, Dict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# If you prefer Selenium Manager (no webdriver-manager), remove this import
# and change build_driver() to webdriver.Chrome(options=chrome_opts)
from webdriver_manager.chrome import ChromeDriverManager

AUDIO_MIME_PREFIXES = ("audio/",)
AUDIO_PATH_HINTS = ("/audio/", ".mp3", ".wav", ".ogg", ".m4a")

# ---------------------------- CONFIG ----------------------------
# Set to None to scrape every clickable audio
LIMIT_TOP_N = None

ENTRY_ROOT_SELECTOR = "#entries"
ENTRY_SELECTOR = "div.entry"
ENG_SELECTOR = ".eng"
ARR_CONTAINER_SELECTOR = ".arr"
# Common "speaker" elements; we try these before falling back to generic spans
ARR_SPEAKER_SELECTORS = ".au, .speak, .fa-volume-up, button, [aria-label*='play' i], [title*='play' i]"
# ----------------------------------------------------------------

REPLACERS = {
    "\u2011": "-",  # non-breaking hyphen
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201C": '"',  # left double quote
    "\u201D": '"',  # right double quote
}

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    for bad, good in REPLACERS.items():
        s = s.replace(bad, good)
    return s.strip()


def build_driver(headless: bool = False) -> webdriver.Chrome:
    chrome_opts = Options()
    if headless:
        chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--ignore-certificate-errors")
    chrome_opts.add_argument("--window-size=1440,1024")
    chrome_opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        pass
    return driver


def is_audio_log(entry: dict) -> Tuple[bool, str]:
    """Detect audio responses in DevTools 'performance' logs."""
    try:
        msg = json.loads(entry.get("message", "{}"))
        method = msg.get("message", {}).get("method", "")
        if method != "Network.responseReceived":
            return (False, "")
        params = msg["message"]["params"]
        response = params.get("response", {}) or {}
        url = (response.get("url") or "").strip()
        mime = (response.get("mimeType") or "").strip()
        if not url:
            return (False, "")
        if any(mime.startswith(p) for p in AUDIO_MIME_PREFIXES):
            return (True, url)
        if any(h in url for h in AUDIO_PATH_HINTS):
            return (True, url)
    except Exception:
        pass
    return (False, "")


def get_new_audio_urls(driver, seen_request_ids: Set[str]) -> List[str]:
    """Return new audio URLs since last check, tracking by requestId to avoid dupes."""
    found_urls: List[str] = []
    logs = driver.get_log("performance")
    for entry in logs:
        try:
            msg = json.loads(entry.get("message", "{}"))
            params = msg.get("message", {}).get("params", {})
            req_id = params.get("requestId")
            if not req_id or req_id in seen_request_ids:
                continue
            is_audio, url = is_audio_log(entry)
            if is_audio and url:
                print(f"[AUDIO-DEVTOOLS] {url}")
                found_urls.append(url)
            seen_request_ids.add(req_id)
        except Exception:
            continue
    return found_urls


@contextmanager
def wait_for_new_audio(driver, seen_request_ids: Set[str], wait_seconds: float = 6.0):
    """Context manager: start/stop a polling window for DevTools audio URLs."""
    start_time = time.time()
    yield lambda: poll_audio(driver, seen_request_ids, start_time, wait_seconds)


def poll_audio(driver, seen_request_ids: Set[str], start_time: float, wait_seconds: float) -> List[str]:
    collected: List[str] = []
    end_time = start_time + wait_seconds
    while time.time() < end_time:
        urls = get_new_audio_urls(driver, seen_request_ids)
        for u in urls:
            if u and u not in collected:
                collected.append(u)
        time.sleep(0.15)
    return collected


def collect_audio_urls_since(driver, t0_ms: float) -> List[str]:
    """Use Performance API and audio/source elements to find recently fetched audio URLs."""
    js = r"""
    const since = arguments[0];
    const urls = new Set();
    try {
      const perf = performance.getEntriesByType('resource');
      for (const e of perf) {
        if (e.startTime >= since) {
          const name = (e.name || '').toString();
          if (/\.(mp3|wav|ogg|m4a)(\?|#|$)/i.test(name) || name.includes('/audio/')) {
            urls.add(name);
          }
        }
      }
    } catch (e) {}
    // Also capture the global audio element (some sites reuse a single player)
    try {
      const a = document.querySelector('audio, video');
      if (a) {
        if (a.currentSrc) urls.add(a.currentSrc);
        if (a.src) urls.add(a.src);
        const srcEl = a.querySelector('source');
        if (srcEl && srcEl.src) urls.add(srcEl.src);
      }
    } catch (e) {}
    return Array.from(urls);
    """
    try:
        return driver.execute_script(js, t0_ms) or []
    except Exception:
        return []


def get_active_audio_src(driver, timeout: float = 6.0) -> str:
    """
    Wait for the page's audio element to expose a non-empty currentSrc/src.
    Also monkey-patch HTMLMediaElement.play to stash last src in window.__lastAudioSrc.
    """
    hook_js = r"""
    if (!window.__audioHooked) {
      try {
        const origPlay = HTMLMediaElement.prototype.play;
        HTMLMediaElement.prototype.play = function(...args) {
          try { window.__lastAudioSrc = this.currentSrc || this.src || ''; } catch(e) {}
          return origPlay.apply(this, args);
        };
        window.__audioHooked = true;
      } catch(e) {}
    }
    """
    try:
        driver.execute_script(hook_js)
    except Exception:
        pass

    end = time.time() + timeout
    last = ""
    while time.time() < end:
        try:
            src = driver.execute_script("""
                const a = document.querySelector('audio, video');
                if (!a) return '';
                return a.currentSrc || a.src || (a.querySelector('source')?.src || '');
            """) or ""
            if not src:
                # try any value set by our hook
                src = driver.execute_script("return window.__lastAudioSrc || ''") or ""
            if src and ("/audio/" in src or src.lower().endswith(('.mp3','.wav','.ogg','.m4a'))):
                return src
            last = src or last
        except Exception:
            pass
        time.sleep(0.15)
    return last or ""


def scroll_into_view(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior:'instant', block:'center'});", element)
    except Exception:
        pass


def prefer_primary(urls: List[str]) -> str:
    """Pick the 'best' URL to treat as primary (prefer /audio/ and .mp3)."""
    if not urls:
        return ""
    def key(u: str):
        u_low = u.lower()
        return ("/audio/" not in u_low, not u_low.endswith(".mp3"), len(u_low))
    return sorted(urls, key=key)[0]


def scrape(out_path: str, headless: bool = False):
    driver = build_driver(headless=headless)
    seen_request_ids: Set[str] = set()

    try:
        driver.get("https://arrernte-angkentye.online/ecall/default.html")

        entries_root = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ENTRY_ROOT_SELECTOR))
        )
        time.sleep(1.0)

        entry_divs = entries_root.find_elements(By.CSS_SELECTOR, ENTRY_SELECTOR)

        # raw rows per click (we'll dedup before writing)
        raw_rows: List[Tuple[str, str, str, str]] = []
        processed_clicks = 0

        for idx, entry in enumerate(entry_divs, start=1):
            # English meaning
            try:
                eng_el = entry.find_element(By.CSS_SELECTOR, ENG_SELECTOR)
                eng_text = clean_text(eng_el.text)
            except Exception:
                eng_text = ""

            # Clickable audio controls
            clickables = []
            try:
                arr_container = entry.find_element(By.CSS_SELECTOR, ARR_CONTAINER_SELECTOR)
                try:
                    clickables = arr_container.find_elements(By.CSS_SELECTOR, ARR_SPEAKER_SELECTORS)
                except Exception:
                    clickables = []
                if not clickables:
                    # fallback to spans
                    clickables = arr_container.find_elements(By.CSS_SELECTOR, "span")
            except Exception:
                pass

            if LIMIT_TOP_N is not None:
                remaining = max(0, LIMIT_TOP_N - processed_clicks)
                clickables = clickables[:remaining]

            if not clickables:
                # still record the entry (no clickable audio found)
                raw_rows.append((eng_text, "", "", ""))
                continue

            for s in clickables:
                if LIMIT_TOP_N is not None and processed_clicks >= LIMIT_TOP_N:
                    break

                # word text fallback
                word = ""
                try:
                    word = clean_text(s.text) or clean_text(arr_container.text)
                except Exception:
                    pass

                try:
                    scroll_into_view(driver, s)
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(s))

                    t0_ms = driver.execute_script("return performance.now();") or 0

                    # poll DevTools in this window
                    with wait_for_new_audio(driver, seen_request_ids, wait_seconds=6.0) as collector:
                        try:
                            s.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", s)
                        time.sleep(0.25)

                    # collect from multiple sources
                    page_audio_urls = collect_audio_urls_since(driver, t0_ms)
                    devtools_audio_urls = collector()
                    current_src = get_active_audio_src(driver, timeout=4.0)

                    all_urls: List[str] = []
                    seen_local = set()
                    for u in page_audio_urls + devtools_audio_urls + [current_src]:
                        if u and u not in seen_local:
                            seen_local.add(u)
                            all_urls.append(u)

                    # fallback: scan within this entry
                    try:
                        entry_audio_js = r"""
                        const root = arguments[0];
                        const urls = new Set();
                        const q = root.querySelectorAll('a, audio, source');
                        q.forEach(el => {
                          const u = (el.href || el.src || '').toString();
                          if (u && (u.includes('/audio/') || /\.(mp3|wav|ogg|m4a)(\?|#|$)/i.test(u))) urls.add(u);
                        });
                        return Array.from(urls);
                        """
                        extra_urls = driver.execute_script(entry_audio_js, entry) or []
                    except Exception:
                        extra_urls = []
                    for u in extra_urls:
                        if u and u not in seen_local:
                            seen_local.add(u)
                            all_urls.append(u)

                    primary = prefer_primary(all_urls)
                    print(f"[WORD] {word} | [ENG] {eng_text} | [AUDIO] {primary}")
                    for u in all_urls:
                        print(f"[AUDIO-ALL] {u}")

                    raw_rows.append((eng_text, word, primary, " | ".join(all_urls)))
                    processed_clicks += 1
                    time.sleep(0.1)

                except Exception as e:
                    print(f"[WARN] Click/collect failed for '{word}': {e}")
                    fallback_src = get_active_audio_src(driver, timeout=2.5)
                    raw_rows.append((eng_text, word, fallback_src, fallback_src or ""))
                    processed_clicks += 1

        # ---------- Deduplicate: one row per (english_meaning, arrernte_word) ----------
        by_word: Dict[Tuple[str, str], Dict[str, object]] = {}
        for eng, word, primary, all_urls in raw_rows:
            key = (eng or "", word or "")
            rec = by_word.get(key)
            if not rec:
                rec = {"eng": eng or "", "word": word or "", "urls": [], "primary": ""}
                by_word[key] = rec

            # add URLs
            if all_urls:
                for u in [x.strip() for x in all_urls.split("|")]:
                    if u and u not in rec["urls"]:
                        rec["urls"].append(u)

            # set a primary if missing and we have one
            if (not rec["primary"]) and primary:
                rec["primary"] = primary

        # if primary still empty, pick from aggregated list
        for rec in by_word.values():
            if not rec["primary"]:
                rec["primary"] = prefer_primary(rec["urls"])

        rows_out = list(by_word.values())

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["english_meaning", "arrernte_word", "audio_url", "all_audio_urls"])
            for rec in rows_out:
                writer.writerow([rec["eng"], rec["word"], rec["primary"], " | ".join(rec["urls"])])

        print(f"Saved {len(rows_out)} rows to {out_path}")

    finally:
        driver.quit()


def main():
    ap = argparse.ArgumentParser(description="Scrape Arrernte words, meanings, and audio URLs; emit one row per word.")
    ap.add_argument("--out", default="arrernte_audio.csv", help="Output CSV path")
    ap.add_argument("--headless", action="store_true", help="Run Chrome headless (default is visible)")
    args = ap.parse_args()
    scrape(out_path=args.out, headless=args.headless)


if __name__ == "__main__":
    main()
