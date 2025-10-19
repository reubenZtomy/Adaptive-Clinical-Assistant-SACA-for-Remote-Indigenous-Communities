#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arrernte <-> English glossary translator (terminal app)

Key features
- Auto-detects CSV columns (english_meaning, arrernte_word, audio_url, all_audio_urls)
- Phrase-first matching; single-word fallback
- Light context scoring using English-meaning tokens
- EN->ARR: drops 'a/an/the' by default (use --keep-articles to keep)
- ARR->EN: returns ONE clean English gloss (first or shortest synonym)
- Optional round-trip check
- Debug mode shows match decisions and scores

Usage examples
  python glossary_translator.py -g arrernte_audio.csv -m en2arr -t "I have a very bad headache." -r --showaudio --debug
  python glossary_translator.py -g arrernte_audio.csv -m arr2en -t "ayenge atnyeneme arnterre." -r --debug
"""

import argparse
import csv
import re
import sys
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple, Optional

WORD_RE = re.compile(r"[A-Za-z’']+|[.,;:!?]")

# ---------- Helpers ----------

def tokenize(s: str) -> List[str]:
    # lowercase & keep basic punctuation tokens
    return re.findall(WORD_RE, s.lower())

def is_word(tok: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z’']+", tok))

def detok(tokens: List[str]) -> str:
    # join, then fix spacing before punctuation; also collapse duplicate punctuation
    s = " ".join(tokens)
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)
    s = re.sub(r"([.!?])\1+", r"\1", s)  # .. -> .
    return s

def coarse_pos(tag: str) -> str:
    if tag.startswith("NN"): return "noun"
    if tag.startswith("VB"): return "verb"
    if tag.startswith("JJ"): return "adj"
    if tag.startswith("RB"): return "adv"
    return ""

def try_pos_tag_english(tokens: List[str]) -> Dict[str, str]:
    # Optional: POS tags for English tokens; degrade gracefully if nltk unavailable
    try:
        import nltk
        try:
            nltk.data.find("taggers/averaged_perceptron_tagger")
        except LookupError:
            nltk.download("averaged_perceptron_tagger", quiet=True)
        words = [t for t in tokens if is_word(t)]
        tagged = nltk.pos_tag(words)
        return {w: coarse_pos(p) for (w, p) in tagged}
    except Exception:
        return {}

def overlap_score(context_tokens: List[str], hints: List[str]) -> float:
    if not hints: return 0.0
    ctx = Counter(context_tokens)
    return sum(ctx[w] for w in hints) / (len(hints) + 1e-9)

def split_synonyms(english_meaning: str) -> List[str]:
    # "hold, have, keep" -> ["hold","have","keep"]
    parts = [p.strip().lower() for p in english_meaning.split(",")]
    return [p for p in parts if p]

# ---------- Auto column detection ----------

def _pick_col(headers_norm_map: Dict[str,str], candidates=None, contains_any=None, required=True, label=""):
    """
    headers_norm_map: {normalized_header: original_header}
    """
    if candidates:
        for c in candidates:
            if c in headers_norm_map:
                return headers_norm_map[c]
    if contains_any:
        for norm, orig in headers_norm_map.items():
            if all(tok in norm for tok in contains_any):
                return orig
    if required:
        need = " or ".join(candidates or []) or " / ".join(contains_any or [])
        raise SystemExit(f"CSV is missing a required column ({label}). "
                         f"Looked for: {need}. Headers found: {list(headers_norm_map.values())}")
    return None

# ---------- Glossary ----------

class Glossary:
    def __init__(self, rows: List[Dict[str, Any]]):
        self.rows = rows

        # EN->ARR indices
        self.phrase_en = defaultdict(list)
        self.word_en   = defaultdict(list)
        self.max_phrase_en = 1

        # ARR->EN indices
        self.phrase_arr = defaultdict(list)
        self.word_arr   = defaultdict(list)
        self.max_phrase_arr = 1

        for row in rows:
            for en_key_str in row["en_keys"]:
                en_tok = tuple(tokenize(en_key_str))
                if len(en_tok) > 1:
                    self.phrase_en[en_tok].append(row)
                elif len(en_tok) == 1:
                    self.word_en[en_tok[0]].append(row)

            arr_tok = tuple(tokenize(row["arrernte_word"]))
            if len(arr_tok) > 1:
                self.phrase_arr[arr_tok].append(row)
            elif len(arr_tok) == 1:
                self.word_arr[arr_tok[0]].append(row)

        if self.phrase_en:
            self.max_phrase_en = max(len(k) for k in self.phrase_en.keys())
        if self.phrase_arr:
            self.max_phrase_arr = max(len(k) for k in self.phrase_arr.keys())

    @staticmethod
    def load_csv(path: str) -> "Glossary":
        rows: List[Dict[str, Any]] = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise SystemExit("CSV appears empty or has no header row.")

            headers_norm_map = { (h or "").strip().lower(): (h or "") for h in reader.fieldnames }

            en_col = _pick_col(
                headers_norm_map,
                candidates=["english_meaning", "english meanings", "english meaning", "english_m", "english"],
                contains_any=["english"],
                required=True,
                label="English meaning"
            )
            arr_col = _pick_col(
                headers_norm_map,
                candidates=["arrernte_word", "arrernte", "arr word", "arrernte word", "arrernte_word_"],
                contains_any=["arrernte"],
                required=True,
                label="Arrernte word"
            )
            audio_col = _pick_col(
                headers_norm_map,
                candidates=["audio_url", "audio url"],
                contains_any=["audio", "url"],
                required=False,
                label="audio url"
            )
            all_audio_col = _pick_col(
                headers_norm_map,
                candidates=["all_audio_urls", "all audio urls"],
                contains_any=["all","audio","url"],
                required=False,
                label="all audio urls"
            )

            for r in reader:
                english_meaning = (r.get(en_col) or "").strip()
                arr = (r.get(arr_col) or "").strip()
                audio = (r.get(audio_col) or "").strip() if audio_col else ""
                all_audios_raw = (r.get(all_audio_col) or "").strip() if all_audio_col else ""
                # split all_audio_urls by whitespace or commas
                all_urls = [u.strip() for u in re.split(r"[\s,]+", all_audios_raw) if u.strip()]
                if not audio and all_urls:
                    audio = all_urls[0]

                en_keys = split_synonyms(english_meaning)
                hint_tokens: List[str] = []
                for k in en_keys:
                    hint_tokens.extend([t for t in tokenize(k) if is_word(t)])

                # Choose a primary English gloss for ARR->EN display
                primary_en = en_keys[0] if en_keys else english_meaning.strip().lower()

                rows.append({
                    "english_meaning": english_meaning,
                    "arrernte_word": arr,
                    "audio_url": audio,
                    "all_audio_urls": all_urls,
                    "en_keys": en_keys,
                    "hint_tokens": hint_tokens,
                    "primary_en": primary_en
                })

        return Glossary(rows)

# ---------- Translation core ----------

STOPWORDS_EN_ARTICLES = {"a","an","the"}

def lookup(g: Glossary, tokens: List[str], i: int, direction: str) -> Tuple[int, List[Dict[str, Any]]]:
    if direction == "en2arr":
        maxL, P, W = g.max_phrase_en, g.phrase_en, g.word_en
    else:
        maxL, P, W = g.max_phrase_arr, g.phrase_arr, g.word_arr
    # try phrases first (longest to shortest)
    for L in range(min(maxL, len(tokens) - i), 1, -1):
        span = tuple(tokens[i:i+L])
        if span in P:
            return L, P[span]
    # single token
    return 1, W.get(tokens[i], [])

def score(entry: Dict[str, Any], context_tokens: List[str]) -> float:
    s = 0.0
    s += 1.0 * overlap_score(context_tokens, entry["hint_tokens"])
    # small preference for entries indexed by longer English phrases
    longest_key_len = max((len(tokenize(k)) for k in entry["en_keys"]), default=1)
    s += 0.1 * (longest_key_len - 1)
    return s

def translate(
    g: Glossary,
    text: str,
    direction: str = "en2arr",
    min_score: float = -999,
    debug: bool = False,
    drop_articles: bool = True,
    arr2en_choice: str = "first"  # "first" or "shortest"
):
    tokens = tokenize(text)
    out_tokens: List[str] = []
    decisions: List[Dict[str, Any]] = []

    i = 0
    while i < len(tokens):
        # Optional: drop English articles during EN->ARR if they don't match any glossary entry
        if direction == "en2arr" and is_word(tokens[i]) and tokens[i] in STOPWORDS_EN_ARTICLES:
            # Lookahead: only drop if there's no explicit dictionary entry for this article
            _, maybe = lookup(g, tokens, i, direction)
            if not maybe:
                if debug:
                    print(f"[DEBUG] dropping article: {tokens[i]}")
                i += 1
                continue

        consumed, cands = lookup(g, tokens, i, direction)
        span = tokens[i:i+consumed]

        # context window
        left = tokens[max(0, i-3):i]
        right = tokens[i+consumed:i+consumed+3]
        window = [w for w in (left + right) if is_word(w)]

        chosen = None
        if cands:
            scored = [(score(e, window), e) for e in cands]
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored[0][0] > min_score:
                chosen = scored[0]

        if chosen:
            sc, e = chosen
            if direction == "en2arr":
                tgt = e["arrernte_word"]
                out_tokens.extend(tgt.split(" "))
            else:
                # choose ONE clean English gloss to emit
                if e["en_keys"]:
                    if arr2en_choice == "shortest":
                        tgt = min(e["en_keys"], key=lambda k: len(k))
                    else:
                        tgt = e["en_keys"][0]  # first by default
                else:
                    tgt = e["primary_en"] or e["english_meaning"]
                out_tokens.extend(tgt.split(" "))

            decisions.append({
                "src_span": detok(span),
                "tgt": tgt,
                "score": round(sc, 3),
                "audio_urls": [e["audio_url"]] if (direction == "en2arr" and e["audio_url"]) else []
            })
            i += consumed
        else:
            passthrough = detok(span)
            out_tokens.extend(passthrough.split(" "))
            decisions.append({"src_span": detok(span), "tgt": passthrough, "score": -999, "audio_urls": []})
            i += consumed

    out_text = detok(out_tokens)
    if debug:
        print("\n[DEBUG choices]")
        for d in decisions:
            print(f"  {d['src_span']:<18} -> {d['tgt']:<20}  score={d['score']}")
    return out_text, decisions

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Arrernte <-> English glossary translator (terminal)")
    ap.add_argument("-g","--glossary", required=True, help="Path to glossary CSV")
    ap.add_argument("-m","--mode", choices=["en2arr","arr2en"], default="en2arr", help="Direction")
    ap.add_argument("-t","--text", help="Inline text. If omitted, reads from STDIN.")
    ap.add_argument("-r","--roundtrip", action="store_true", help="Translate forward then back and compare")
    ap.add_argument("--minscore", type=float, default=-999.0, help="Minimum candidate score to accept")
    ap.add_argument("--debug", action="store_true", help="Show match choices and scores")
    ap.add_argument("--showaudio", action="store_true", help="List audio URLs (EN->ARR only)")
    ap.add_argument("--keep-articles", action="store_true", help="Do NOT drop a/an/the on EN->ARR")
    ap.add_argument("--arr2en-choice", choices=["first","shortest"], default="first",
                    help="When multiple English synonyms exist for an Arrernte word, which to emit")
    args = ap.parse_args()

    g = Glossary.load_csv(args.glossary)
    src = (args.text.strip() if args.text else sys.stdin.read().strip())
    if not src:
        sys.exit("No input text provided.")

    out, decisions = translate(
        g,
        src,
        direction=args.mode,
        min_score=args.minscore,
        debug=args.debug,
        drop_articles=not args.keep_articles,
        arr2en_choice=args.arr2en_choice
    )

    print("\n[{}]".format("English -> Arrernte" if args.mode=="en2arr" else "Arrernte -> English"))
    print(out)

    if args.mode=="en2arr" and args.showaudio:
        urls = [u for d in decisions for u in d["audio_urls"] if u]
        if urls:
            print("\nAudio URLs:")
            for u in urls:
                print(" -", u)

    if args.roundtrip:
        rev = "arr2en" if args.mode=="en2arr" else "en2arr"
        back, _ = translate(g, out, direction=rev, min_score=args.minscore, debug=False)
        print("\n[Round-trip]")
        print("Original :", src)
        print("Back     :", back)

        # simple token diff
        def canon(s: str) -> List[str]: return [t for t in tokenize(s)]
        a, b = canon(src), canon(back)
        if a == b:
            print("✅ Exact round-trip match.")
        else:
            i = 0
            while i < min(len(a), len(b)) and a[i] == b[i]:
                i += 1
            if i < min(len(a), len(b)):
                print(f"⚠️  First difference at token {i}: '{a[i]}' vs '{b[i]}'")
            if len(a)!=len(b):
                print(f"⚠️  Length differs: {len(a)} vs {len(b)}")

if __name__ == "__main__":
    main()
