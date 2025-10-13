#!/usr/bin/env python3
import argparse, csv, re, sys, unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://arrernte-angkentye.online"
URL  = f"{BASE}/ecall/"

# ---------- text normalization helpers ----------

_HYPHENS = r"[\u2010\u2011\u2012\u2013\u2014\u2212\u00AD]"  # hyphen-like chars
_QUOTES  = {
    "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"',
    "\u201A": ",", "\u201E": '"',
}
def clean_text(s: str) -> str:
    """Normalize to display-friendly ASCII-ish punctuation (for CSV/Excel)."""
    if not s:
        return ""
    # NFC/NFKC to fold compatibility glyphs (incl. superscripts, width variants)
    s = unicodedata.normalize("NFKC", s)
    # Replace curly quotes
    for k, v in _QUOTES.items():
        s = s.replace(k, v)
    # Normalize all hyphen-like glyphs to ASCII '-'
    s = re.sub(_HYPHENS, "-", s)
    # Collapse spaces around hyphens ( "a - b" -> "a-b" )
    s = re.sub(r"\s*-\s*", "-", s)
    # Collapse internal whitespace
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return s.strip()

def excel_safe(s: str) -> str:
    """
    Prevent Excel from treating content as a formula or throwing #NAME?.
    We insert a ZERO-WIDTH SPACE if the first visible char is one of = + - @.
    """
    if not s:
        return s
    t = s.lstrip()
    if t and t[0] in ("=", "+", "-", "@"):
        return "\u200B" + s  # visually unchanged, Excel-safe
    return s

def norm_slug(text: str) -> str:
    """Slug used by the site's audio files."""
    s = clean_text(text)
    # Strip trailing sense digits (e.g., 'ahentye1'/'ahentye 1' -> 'ahentye')
    s = re.sub(r"\s*\d+$", "", s)
    # Remove spaces, punctuation except hyphen
    s = re.sub(r"[^A-Za-z0-9\- ]", "", s)
    s = s.replace(" ", "")
    return s.lower()

# ---------- scraping ----------

def fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (ArrernteScraper/1.1)"}
    r = requests.get(url, headers=headers, timeout=30)
    # Force correct decode (site is UTF-8)
    r.encoding = "utf-8"
    r.raise_for_status()
    return r.text

def extract_entries(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows_trans, rows_audio = [], []

    for entry in soup.select(".entry"):
        arr = entry.find("div", class_="arr")
        eng = entry.find("div", class_="eng")
        if not arr or not eng:
            continue

        english = clean_text(eng.get_text(" ", strip=True))
        if not english:
            continue

        # Prefer all visible <span class="au"> … </span> (native forms)
        forms = [clean_text(s.get_text(" ", strip=True))
                 for s in arr.find_all("span", class_="au")]
        if not forms:
            # fallback to raw headword text
            raw = clean_text(arr.get_text(" ", strip=True))
            if raw:
                # If comma-separated variants are present, keep them all
                forms = [clean_text(x) for x in re.split(r"\s*,\s*", raw)]

        # Add rows (one per native variant)
        for f in forms:
            if not f:
                continue
            rows_trans.append((excel_safe(f), english))
            slug = norm_slug(f)
            if slug:
                rows_audio.append((excel_safe(f), f"{BASE}/ecall/audio/{slug}.mp3"))

    # de-duplicate while preserving order
    def dedup(seq):
        seen = set(); out = []
        for item in seq:
            if item not in seen:
                seen.add(item); out.append(item)
        return out

    return dedup(rows_trans), dedup(rows_audio)

# ---------- writers ----------

def write_csv(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig => adds BOM so Excel picks UTF-8 correctly on Windows
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Scrape Arrernte entries → CSVs")
    ap.add_argument("--url", default=URL)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--translations", default="arrernte_translations.csv")
    ap.add_argument("--audio", default="arrernte_audio_links.csv")
    args = ap.parse_args()

    html = fetch_html(args.url)
    translations, audio = extract_entries(html)

    outdir = Path(args.outdir)
    write_csv(outdir / args.translations, ["Native", "English"], translations)
    write_csv(outdir / args.audio, ["Native", "AudioURL"], audio)

    print(f"Translations: {len(translations)} rows → {outdir / args.translations}")
    print(f"Audio links : {len(audio)} rows → {outdir / args.audio}")

if __name__ == "__main__":
    main()
