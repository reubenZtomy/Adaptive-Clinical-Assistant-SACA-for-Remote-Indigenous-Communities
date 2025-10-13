from __future__ import annotations
import csv, re
from pathlib import Path

SUPPORTED_TEXT_LANGS = {"en", "pjt"}  # ISO 639-3 for Pitjantjatjara

def normalize_lang(code: str | None) -> str | None:
    if code is None:
        return None
    c = code.lower()
    if c.startswith("en"):
        return "en"
    if c in {"pjt", "pitjantjatjara"}:
        return "pjt"
    return c

def _as_text(v) -> str:
    """Coerce any CSV cell into a clean string (handles None, lists, numbers)."""
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v if x is not None)
    return str(v)

def _normalize_header(name: str) -> str:
    """
    Map a variety of header names to canonical keys.
    Supports both legacy (en/pjt) and new (english_meaning/arrernte_word/audio_url).
    """
    n = (name or "").strip().lower().lstrip("\ufeff")
    if n in {"en", "english"} or "english" in n:
        return "english_meaning"
    if n in {"pjt", "pitjantjatjara"} or "arrernte" in n:
        return "arrernte_word"
    if "audio" in n or "url" in n:
        return "audio_url"
    return n

def load_glossary(csv_path: str | Path) -> dict[str, dict[str, str]]:
    """
    Load glossary from CSV/TSV with robust parsing and column normalization.

    Accepts either:
      - en,pjt
      - english_meaning,arrernte_word[,audio_url]
    """
    csv_path = Path(csv_path)
    en2pjt: dict[str, str] = {}
    pjt2en: dict[str, str] = {}

    if not csv_path.exists():
        return {"en->pjt": en2pjt, "pjt->en": pjt2en}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except Exception:
            # Your file is often TSV; fall back to tab if sniffing fails
            class _Dialect(csv.excel):
                delimiter = "\t"
            dialect = _Dialect

        reader = csv.DictReader(f, dialect=dialect)

        # Normalize headers
        if reader.fieldnames:
            reader.fieldnames = [_normalize_header(fn) for fn in reader.fieldnames]

        for raw_row in reader:
            # Coerce every value to a clean string and re-key with normalized headers
            row = { _normalize_header(k): _as_text(v).strip() for k, v in (raw_row or {}).items() }

            # Accept both legacy and new names (after normalization)
            en  = row.get("english_meaning") or row.get("en")  or row.get("english")
            pjt = row.get("arrernte_word")   or row.get("pjt") or row.get("pitjantjatjara")
            # audio = row.get("audio_url")  # kept in case you later want to expose it

            if not en and not pjt:
                continue

            if en and pjt:
                en_l  = en.lower()
                pjt_l = pjt.lower()
                # Prefer first-seen mapping; don't overwrite on duplicates
                en2pjt.setdefault(en_l, pjt)
                pjt2en.setdefault(pjt_l, en)

    return {"en->pjt": en2pjt, "pjt->en": pjt2en}

def glossary_translate(text: str, src: str, tgt: str, lex: dict[str, dict[str, str]]) -> str:
    if src == tgt or not text.strip():
        return text
    table = lex.get(f"{src}->{tgt}", {})
    if not table:
        return text

    # replace longer phrases first
    items = sorted(table.items(), key=lambda kv: len(kv[0]), reverse=True)

    def preserve_case(src_token: str, repl: str) -> str:
        if src_token.isupper():
            return repl.upper()
        if src_token.istitle():
            return repl[:1].upper() + repl[1:]
        return repl

    out = text
    for src_phrase, tgt_phrase in items:
        pattern = re.compile(rf"\b{re.escape(src_phrase)}\b", re.IGNORECASE)
        out = pattern.sub(lambda m: preserve_case(m.group(0), tgt_phrase), out)
    return out

class GlossaryMT:
    def __init__(self, csv_path: str | Path = "data/glossary.csv"):
        self.lex = load_glossary(csv_path)

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        src = normalize_lang(src_lang) or "en"
        tgt = normalize_lang(tgt_lang) or "en"
        if src not in SUPPORTED_TEXT_LANGS or tgt not in SUPPORTED_TEXT_LANGS:
            return text
        return glossary_translate(text, src, tgt, self.lex)
