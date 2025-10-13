
# app_rev.py
# Arrernte ↔ English Translation/Test API (reverse endpoint forces glossary matching)
#
# What’s new:
# - NEW endpoint: POST /audio/arrernte-to-english
#   * Uses ONLY the CSV glossary audio for reverse translation via audio fingerprint matching.
#   * No Whisper fallback (fails with 501 if librosa/pydub not installed).
# - Existing endpoints/behavior preserved; you can drop-in replace your current app.py
#
# Dependencies:
#   pip install fastapi uvicorn pandas requests pydub librosa
#   (Also ensure ffmpeg is available on PATH; see /health)
#
# Notes:
# - For speed during testing, you can cap the dictionary size with MATCH_DICT_CAP.
#   To use the full glossary, set MATCH_DICT_CAP = None (default).
#
from pathlib import Path
import os, re, unicodedata, tempfile, subprocess, shlex, time, importlib.util, shutil, math, json, hashlib
from typing import List, Optional, Dict, Tuple

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse

import requests

# ---------- Config ----------
HERE = Path(__file__).parent
AUDIO_CSV = HERE / "arrernte_audio.csv"          # your glossary from the crawler
OUTPUT_DIR = HERE / "output_audio"               # for synthesized outputs
CACHE_DIR  = HERE / "dict_cache"                 # persistent cache for dictionary fingerprints
CACHE_DIR.mkdir(exist_ok=True)
RAW_DIR    = CACHE_DIR / "raw"
WAV_DIR    = CACHE_DIR / "wav"
FP_DIR     = CACHE_DIR / "fp"
for d in (RAW_DIR, WAV_DIR, FP_DIR):
    d.mkdir(exist_ok=True)

# Keep your existing test cap for EN->ARR path if you like
TOP_N_TEST_EN2ARR = 5  # REMOVE THIS to lift the cap for english-to-arrernte

# For reverse (ARR->EN) we default to NO CAP so it uses the whole glossary
MATCH_DICT_CAP: Optional[int] = None  # set to e.g. 300 for quicker testing

# ---------- Helper: ensure ffmpeg on PATH ----------
def _ensure_ffmpeg_on_path_for_process() -> bool:
    def _has_ffmpeg():
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return True
        except FileNotFoundError:
            return False

    if _has_ffmpeg():
        return True

    candidates = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(os.path.join(local, "Microsoft", "WinGet", "Links"))
    candidates.append(r"C:\ffmpeg\bin")

    for p in candidates:
        if p and os.path.isdir(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + p

    return _has_ffmpeg()

FFMPEG_OK = _ensure_ffmpeg_on_path_for_process()

# ---------- String utils ----------
def normalize_token(t: str) -> str:
    if not isinstance(t, str):
        return ""
    t = t.lower().strip()
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = re.sub(r"[^\w\-’']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

_word_re = re.compile(r"[A-Za-z']+")

def _eng_tokens(s: str) -> List[str]:
    return [w.lower() for w in _word_re.findall(s or "")]

def simple_tokenize(text: str) -> List[str]:
    text = normalize_token(text)
    if not text:
        return []
    return text.split(" ")

# ---------- Load crawler CSV ----------
if not AUDIO_CSV.exists():
    raise RuntimeError(f"Crawler CSV not found. Expected {AUDIO_CSV}")

_df_audio = pd.read_csv(AUDIO_CSV, encoding="utf-8-sig")
_df_audio["english_meaning"] = _df_audio.get("english_meaning", "").astype(str).fillna("").str.strip()
_df_audio["arrernte_word"]  = _df_audio.get("arrernte_word", "").astype(str).fillna("").str.strip()
_df_audio["audio_url"]      = _df_audio.get("audio_url", "").astype(str).fillna("").str.strip()
if "all_audio_urls" not in _df_audio.columns:
    _df_audio["all_audio_urls"] = ""
_df_audio["all_audio_urls"] = _df_audio["all_audio_urls"].astype(str).fillna("").str.strip()

class AudioRow(BaseModel):
    english_meaning: str
    arrernte_word: str
    audio_url: str
    all_audio_urls: Optional[str] = ""

ROWS: List[AudioRow] = []
for _, r in _df_audio.iterrows():
    arr = str(r.get("arrernte_word", "")).strip()
    if arr:
        ROWS.append(AudioRow(
            english_meaning=str(r.get("english_meaning", "")).strip(),
            arrernte_word=normalize_token(arr),
            audio_url=str(r.get("audio_url", "")).strip(),
            all_audio_urls=str(r.get("all_audio_urls", "")).strip(),
        ))

# Index: english token -> candidate rows (for EN->ARR path)
ENG_TOKEN_TO_ROWS: Dict[str, List[AudioRow]] = {}
for r in ROWS:
    toks = set(_eng_tokens(r.english_meaning))
    for t in toks:
        ENG_TOKEN_TO_ROWS.setdefault(t, []).append(r)

# ---------- Basic naive English → Arrernte (from crawler CSV) ----------
def naive_english_to_arrernte_rows(english_text: str, limit: int = 5) -> List[AudioRow]:
    if not english_text:
        return []
    input_toks = set(_eng_tokens(english_text))
    if not input_toks:
        return []
    pool: Dict[str, AudioRow] = {}
    for tok in input_toks:
        for r in ENG_TOKEN_TO_ROWS.get(tok, []):
            pool[r.arrernte_word] = r
    scored: List[Tuple[int, AudioRow]] = []
    for r in pool.values():
        gloss_toks = set(_eng_tokens(r.english_meaning))
        overlap = len(input_toks & gloss_toks)
        if overlap > 0:
            scored.append((overlap, r))
    if not scored:
        return []
    scored.sort(key=lambda t: (-t[0], t[1].arrernte_word))
    picked = [r for _, r in scored[:limit]]
    return picked

# ---------- FastAPI ----------
app = FastAPI(
    title="Arrernte ↔ English Translation/Test API",
    description="Glossary-backed English→Arrernte and reverse Arrernte→English with audio fingerprint matching (no Whisper fallback).",
    version="2.5.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs")

# ---------- Health ----------
def _cmd_exists(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False

PYTTSX3_AVAILABLE = importlib.util.find_spec("pyttsx3") is not None
ESPEAK_AVAILABLE = _cmd_exists("espeak") or _cmd_exists("espeak-ng")
LIBROSA_AVAILABLE = importlib.util.find_spec("librosa") is not None
PYDUB_AVAILABLE = importlib.util.find_spec("pydub") is not None

@app.get("/health")
def health():
    return {
        "status": "ok",
        "rows_in_csv": len(ROWS),
        "csv_path": str(AUDIO_CSV),
        "ffmpeg_on_path": bool(FFMPEG_OK),
        "espeak_available": ESPEAK_AVAILABLE,
        "pyttsx3_available": PYTTSX3_AVAILABLE,
        "librosa_available": LIBROSA_AVAILABLE,
        "pydub_available": PYDUB_AVAILABLE,
        "output_dir": str(OUTPUT_DIR),
        "cache_dir": str(CACHE_DIR),
        "match_dict_cap": MATCH_DICT_CAP,
        "test_cap_en2arr": TOP_N_TEST_EN2ARR,  # REMOVE THIS later
    }

# ---------- Audio/FFmpeg utilities ----------
def _ffmpeg(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}\n{proc.stderr[:4000]}")

def _download_file(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return dest

def _to_uniform_wav(src: Path, dst_wav: Path) -> Path:
    """Transcode any input to 16kHz mono PCM WAV."""
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-ar", "16000", "-ac", "1", "-f", "wav", "-acodec", "pcm_s16le",
        str(dst_wav),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return dst_wav

def _concat_audio_to_mp3(paths: List[Path], workdir: Path) -> Path:
    if not paths:
        raise ValueError("No audio to concatenate")
    wavs: List[Path] = []
    for i, p in enumerate(paths, start=1):
        dst = workdir / f"norm_{i:04d}.wav"
        _to_uniform_wav(p, dst)
        wavs.append(dst)
    listfile = workdir / "concat_wav.txt"
    with open(listfile, "w", encoding="utf-8") as f:
        for w in wavs:
            f.write(f"file {shlex.quote(str(w))}\n")
    merged_wav = workdir / "merged.wav"
    cmd_wav = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(merged_wav)]
    subprocess.run(cmd_wav, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out_mp3 = workdir / "arrernte_sentence.mp3"
    cmd_mp3 = ["ffmpeg", "-y", "-i", str(merged_wav), "-codec:a", "libmp3lame", "-q:a", "2", str(out_mp3)]
    subprocess.run(cmd_mp3, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return out_mp3

# ---------- Offline English TTS (espeak / pyttsx3) ----------
def _synthesize_english_espeak(text: str, wav_out: Path) -> bool:
    if not ESPEAK_AVAILABLE:
        return False
    cmd_name = "espeak-ng" if _cmd_exists("espeak-ng") else "espeak"
    safe_text = text if text.endswith((".", "?", "!", ",")) else f"{text}."
    cmd = [cmd_name, "-w", str(wav_out), safe_text]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return wav_out.exists() and wav_out.stat().st_size > 400
    except subprocess.CalledProcessError:
        return False

def _synthesize_english_pyttsx3(text: str, wav_out: Path) -> bool:
    if not PYTTSX3_AVAILABLE:
        return False
    try:
        import pyttsx3
        engine = pyttsx3.init()
        try:
            rate = engine.getProperty('rate')
            engine.setProperty('rate', int(rate * 0.9))
        except Exception:
            pass
        safe_text = text if text.endswith((".", "?", "!", ",")) else f"{text}."
        engine.save_to_file(safe_text, str(wav_out))
        engine.runAndWait()
        return wav_out.exists() and wav_out.stat().st_size > 400
    except Exception:
        return False

def synthesize_english_offline(text: str, out_dir: Path, base_name: str) -> Path:
    out_wav = out_dir / f"{base_name}.wav"
    out_dir.mkdir(parents=True, exist_ok=True)
    if _synthesize_english_espeak(text, out_wav):
        return out_wav
    if _synthesize_english_pyttsx3(text, out_wav):
        return out_wav
    raise HTTPException(
        status_code=501,
        detail="No offline TTS engine found. Install 'espeak' (or 'espeak-ng') or add 'pyttsx3' to the venv."
    )

# ================================
# EXISTING: English → Arrernte API
# ================================
class SynthesisIn(BaseModel):
    english_text: str = Field(..., description="English sentence; best-matching Arrernte words are taken from the crawler CSV")
    insert_gap_ms: Optional[int] = Field(0, ge=0, le=2000, description="Optional silence between clips (ms)")

@app.post("/audio/english-to-arrernte", summary="Translate English using crawler CSV, interleave Arrernte clips with offline TTS for unmapped English (in order)")
def english_to_arrernte_tts(payload: SynthesisIn):
    if not FFMPEG_OK:
        raise HTTPException(500, "ffmpeg is not available on PATH (see /health).")

    limit = TOP_N_TEST_EN2ARR or 50  # REMOVE THIS to lift the cap later
    candidates = naive_english_to_arrernte_rows(payload.english_text, limit=limit)

    token_to_rows: Dict[str, List[AudioRow]] = {}
    for r in candidates:
        for tok in set(_eng_tokens(r.english_meaning)):
            token_to_rows.setdefault(tok, []).append(r)

    used_arr: set = set()
    input_tokens = _eng_tokens(payload.english_text)
    plan: List[Tuple[str, Optional[AudioRow], Optional[str]]] = []

    for tok in input_tokens:
        rows_for_tok = [r for r in token_to_rows.get(tok, []) if r.arrernte_word not in used_arr]
        chosen_row = rows_for_tok[0] if rows_for_tok else None
        if chosen_row and chosen_row.audio_url:
            plan.append(("arr", chosen_row, None))
            used_arr.add(chosen_row.arrernte_word)
        else:
            plan.append(("eng", None, tok))

    if not plan:
        raise HTTPException(400, "No tokens to synthesize from the English input.")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        ordered_files: List[Path] = []
        arr_words_used: List[str] = []

        try:
            for idx, (kind, row, eng_tok) in enumerate(plan, start=1):
                if kind == "arr" and row:
                    # prefer primary audio_url
                    mp3_path = RAW_DIR / (hashlib.md5(row.audio_url.encode("utf-8")).hexdigest() + ".mp3")
                    if not mp3_path.exists():
                        _download_file(row.audio_url, mp3_path)
                    ordered_files.append(mp3_path)
                    arr_words_used.append(row.arrernte_word)
                elif kind == "eng" and eng_tok:
                    wav = synthesize_english_offline(eng_tok, work, base_name=f"eng_{idx:04d}")
                    ordered_files.append(wav)

                if payload.insert_gap_ms and idx < len(plan):
                    gap = work / f"gap_{idx:04d}.wav"
                    _ffmpeg([
                        "ffmpeg", "-y",
                        "-f", "lavfi", "-t", str(payload.insert_gap_ms / 1000.0),
                        "-i", "anullsrc=r=16000:cl=mono", str(gap)
                    ])
                    ordered_files.append(gap)

            if not ordered_files:
                raise HTTPException(404, detail="Nothing to synthesize.")

            out_mp3 = _concat_audio_to_mp3(ordered_files, work)
            label = "-".join(arr_words_used)[:40] if arr_words_used else "mixed"
            label = re.sub(r"[^a-z0-9\-]+", "_", label.lower()) or "arrernte"
            final_name = f"{label}-{int(time.time())}.mp3"
            OUTPUT_DIR.mkdir(exist_ok=True)
            final_path = OUTPUT_DIR / final_name
            shutil.move(str(out_mp3), str(final_path))

            headers = {
                "X-Arrernte-Words": ", ".join(arr_words_used),
                "X-Word-Count": str(len(arr_words_used)),
                "X-Plan-Length": str(len(plan)),
                "X-Test-Cap-EN2ARR": str(TOP_N_TEST_EN2ARR) if TOP_N_TEST_EN2ARR else "",
            }

            return FileResponse(
                path=str(final_path),
                media_type="audio/mpeg",
                filename=final_name,
                headers=headers
            )

        except requests.RequestException as e:
            raise HTTPException(502, f"Failed to download audio: {e}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Audio synthesis failed: {type(e).__name__}: {e}")

# ===========================================
# NEW: Strict Arrernte audio → English (glossary)
# ===========================================

def _lib_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None

def _safe_float(x: float) -> float:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return 0.0
    return float(x)

def _compute_mfcc_fingerprint(wav_path: Path):
    """Compute a compact MFCC-based fingerprint and return (vector, duration_sec)."""
    import librosa
    import numpy as np
    y, sr = librosa.load(str(wav_path), sr=16000, mono=True)
    if y.size == 0:
        return [0.0]*20, 0.0
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    vec = np.mean(mfcc, axis=1)  # 20-d
    vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
    return vec.tolist(), float(len(y)/sr)

def _cosine_sim(a: List[float], b: List[float]) -> float:
    import numpy as np
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    na = np.linalg.norm(va) + 1e-9
    nb = np.linalg.norm(vb) + 1e-9
    return float(np.dot(va, vb) / (na * nb))

def _segment_wav_by_silence(wav_path: Path, out_dir: Path) -> List[Path]:
    """Split on silence into segments using pydub; fallback to whole file if pydub missing."""
    if not PYDUB_AVAILABLE:
        return [wav_path]
    from pydub import AudioSegment, silence
    audio = AudioSegment.from_wav(str(wav_path))
    chunks = silence.split_on_silence(audio, min_silence_len=250, silence_thresh=audio.dBFS - 20, keep_silence=120)
    if not chunks:
        seg_path = out_dir / "seg_0001.wav"
        audio.export(str(seg_path), format="wav")
        return [seg_path]
    seg_paths = []
    for i, ch in enumerate(chunks, start=1):
        seg_path = out_dir / f"seg_{i:04d}.wav"
        ch.export(str(seg_path), format="wav")
        seg_paths.append(seg_path)
    return seg_paths

def _hash(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def _ensure_cached_fingerprint(url: str) -> Tuple[Path, List[float]]:
    """
    Ensure we have: raw MP3, normalized WAV, and a fingerprint JSON for the dictionary clip.
    Returns (wav_path, fp_vector).
    """
    hid = _hash(url)
    raw_mp3 = RAW_DIR / f"{hid}.mp3"
    wav_path = WAV_DIR / f"{hid}.wav"
    fp_json = FP_DIR / f"{hid}.json"

    if not raw_mp3.exists():
        _download_file(url, raw_mp3)
    if not wav_path.exists():
        _to_uniform_wav(raw_mp3, wav_path)
    if fp_json.exists():
        try:
            data = json.loads(fp_json.read_text("utf-8"))
            return wav_path, data["vec"]
        except Exception:
            pass  # recompute if cache corrupt

    vec, _dur = _compute_mfcc_fingerprint(wav_path)
    fp_json.write_text(json.dumps({"vec": vec}), encoding="utf-8")
    return wav_path, vec

def _prepare_dictionary_index(limit: Optional[int]) -> List[Tuple[AudioRow, Path, List[float]]]:
    """Build (or load from cache) WAV + fingerprint for each glossary clip."""
    items: List[Tuple[AudioRow, Path, List[float]]] = []
    count = 0
    for r in ROWS:
        if not r.audio_url:
            continue
        try:
            wav_path, vec = _ensure_cached_fingerprint(r.audio_url)
            items.append((r, wav_path, vec))
            count += 1
            if limit and count >= limit:
                break
        except Exception:
            continue
    return items

def _match_segments_to_dictionary(seg_paths: List[Path], dict_items: List[Tuple[AudioRow, Path, List[float]]]) -> List[Dict[str, str]]:
    """Cosine match each segment to the nearest glossary clip."""
    results: List[Dict[str, str]] = []
    for i, sp in enumerate(seg_paths, start=1):
        try:
            vec, dur = _compute_mfcc_fingerprint(sp)
        except Exception:
            results.append({"segment_index": str(i), "english": "", "arrernte_guess": "", "confidence": "0.00", "duration_sec": "0.00"})
            continue

        best_row = None
        best_sim = -1.0
        for r, _w, v in dict_items:
            sim = _cosine_sim(vec, v)
            if sim > best_sim:
                best_sim, best_row = sim, r

        if best_row is None:
            results.append({"segment_index": str(i), "english": "", "arrernte_guess": "", "confidence": "0.00", "duration_sec": f"{_safe_float(dur):.2f}"})
        else:
            results.append({
                "segment_index": str(i),
                "english": best_row.english_meaning,
                "arrernte_guess": best_row.arrernte_word,
                "confidence": f"{_safe_float(best_sim):.2f}",
                "duration_sec": f"{_safe_float(dur):.2f}",
            })
    return results


# ---- Hybrid settings for ARR->EN ----
MATCH_CONFIDENCE = float(os.environ.get("ARR_EN_MATCH_CONF", "0.58"))  # cosine threshold to treat as Arrernte
EN_ASR_ENABLED = os.environ.get("ARR_EN_ENABLE_EN_ASR", "1") != "0"     # allow English-only ASR on low-confidence segments

WHISPER_AVAILABLE = importlib.util.find_spec("whisper") is not None

def _transcribe_english_segment(wav_path: Path) -> str:
    """
    Try to transcribe an English segment.
    Prefers Whisper with task='transcribe' and language='en' (no translation).
    Returns a plain string (can be empty).
    """
    if not EN_ASR_ENABLED:
        return ""
    # Prefer Whisper if available
    if WHISPER_AVAILABLE:
        try:
            import whisper
            model_name = os.environ.get("WHISPER_MODEL", "tiny")
            try:
                model = whisper.load_model(model_name)
            except Exception:
                model = whisper.load_model("tiny")
            res = model.transcribe(str(wav_path), task="transcribe", language="en")
            txt = (res or {}).get("text", "").strip()
            return txt
        except Exception:
            return ""
    # Optionally, add Vosk/PocketSphinx hooks here if installed
    return ""

def _likely_arrernte_by_score_and_length(best_sim: float, dur_sec: float) -> bool:
    """
    Heuristic: short clips with similarity >= threshold are Arrernte words;
    longer clips are more likely English even with some similarity noise.
    """
    if dur_sec <= 0.0:
        return best_sim >= MATCH_CONFIDENCE
    if dur_sec < 1.2:
        return best_sim >= MATCH_CONFIDENCE
    if dur_sec < 2.5:
        return best_sim >= (MATCH_CONFIDENCE + 0.05)
    # very long → strongly bias to English
    return best_sim >= (MATCH_CONFIDENCE + 0.1)

def _space_fix(s: str) -> str:
    # clean spacing around punctuation
    s = s.replace(" ,", ",").replace(" .", ".").replace(" !", "!").replace(" ?", "?").replace(" ;", ";").replace(" :", ":")
    s = s.replace("( ", "(").replace(" )", ")")
    s = s.replace(" '", "'")
    # collapse multiple spaces
    import re as _re
    s = _re.sub(r"\s+", " ", s).strip()
    # Capitalize first letter if looks like a sentence
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s

def _arrernte_to_english_via_glossary_hybrid(src_audio: Path):
    """
    Hybrid reverse translation:
      - Segment by silence (if possible)
      - For each segment: compute cosine similarity to glossary
          * If likely Arrernte → use the glossary English gloss
          * Else → run EN-only ASR and insert raw English so it stays "between words"
      - Finally build a full sentence in sequence
    """
    if not FFMPEG_OK:
        raise HTTPException(500, "ffmpeg is not available on PATH (see /health).")
    if not LIBROSA_AVAILABLE:
        raise HTTPException(501, "librosa not installed. Install with: pip install librosa")
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        wav = tdir / "input.wav"
        _to_uniform_wav(src_audio, wav)

        segments = _segment_wav_by_silence(wav, tdir)
        dict_items = _prepare_dictionary_index(limit=MATCH_DICT_CAP)
        if not dict_items:
            raise HTTPException(502, "No glossary audio available or fingerprint cache failed.")

        ordered_tokens = []  # list of dicts with type, text, meta
        for i, sp in enumerate(segments, start=1):
            try:
                vec, dur = _compute_mfcc_fingerprint(sp)
            except Exception:
                ordered_tokens.append({"index": i, "type": "unknown", "text": ""})
                continue

            best_row = None
            best_sim = -1.0
            for r, _w, v in dict_items:
                sim = _cosine_sim(vec, v)
                if sim > best_sim:
                    best_sim, best_row = sim, r

            if best_row is not None and _likely_arrernte_by_score_and_length(best_sim, dur):
                ordered_tokens.append({
                    "index": i,
                    "type": "arr",
                    "text": best_row.english_meaning,
                    "arrernte_guess": best_row.arrernte_word,
                    "confidence": round(best_sim, 3),
                    "duration_sec": round(dur, 2)
                })
            else:
                # English-only ASR for this segment
                english_txt = _transcribe_english_segment(sp).strip()
                ordered_tokens.append({
                    "index": i,
                    "type": "en" if english_txt else "unknown",
                    "text": english_txt,
                    "arrernte_guess": "",
                    "confidence": "" if not english_txt else "asr",
                    "duration_sec": round(dur, 2)
                })

        # build sentence preserving order
        raw_sentence = " ".join([t["text"] for t in ordered_tokens if t.get("text")])
        full_sentence = _space_fix(raw_sentence)

        return {
            "mode": "audio-match+en-asr",
            "tokens": ordered_tokens,
            "english_sentence": full_sentence,
            "notes": "Arrernte via glossary matching, embedded English via EN-only ASR (Whisper if available)."
        }

def _arrernte_to_english_via_glossary(src_audio: Path):
    # (kept for backwards-compat but unused in route)
    return _arrernte_to_english_via_glossary_hybrid(src_audio)


    """STRICT glossary-based reverse translation (no Whisper)."""
    if not FFMPEG_OK:
        raise HTTPException(500, "ffmpeg is not available on PATH (see /health).")
    if not LIBROSA_AVAILABLE:
        raise HTTPException(501, "librosa not installed. Install with: pip install librosa")
    # pydub is optional; without it we won't segment by silence.
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        wav = tdir / "input.wav"
        _to_uniform_wav(src_audio, wav)

        segments = _segment_wav_by_silence(wav, tdir)
        dict_items = _prepare_dictionary_index(limit=MATCH_DICT_CAP)
        if not dict_items:
            raise HTTPException(502, "No glossary audio available or fingerprint cache failed.")

        matches = _match_segments_to_dictionary(segments, dict_items)
        english_sentence = " ".join([m["english"] for m in matches if m.get("english")])

        return {
            "mode": "audio-match",
            "segments": matches,
            "english_guess": english_sentence.strip(),
            "notes": "Strict glossary audio match using MFCC cosine similarity (no Whisper)."
        }


from fastapi import Form

def _english_audio_to_english_text(src_audio: Path):
    """Direct English ASR (no glossary). Segments by silence if possible; concatenates in order."""
    if not FFMPEG_OK:
        raise HTTPException(500, "ffmpeg is not available on PATH (see /health).")
    if not WHISPER_AVAILABLE:
        raise HTTPException(501, "Whisper not installed. Install with: pip install openai-whisper")
    import whisper
    model_name = os.environ.get("WHISPER_MODEL", "tiny")
    try:
        model = whisper.load_model(model_name)
    except Exception:
        model = whisper.load_model("tiny")

    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        wav = tdir / "input.wav"
        _to_uniform_wav(src_audio, wav)
        segments = _segment_wav_by_silence(wav, tdir)
        tokens = []
        sentence_parts = []
        for i, sp in enumerate(segments, start=1):
            try:
                res = model.transcribe(str(sp), task="transcribe", language="en")
                txt = (res or {}).get("text", "").strip()
            except Exception:
                txt = ""
            if txt:
                tokens.append({"index": i, "type": "en", "text": txt, "confidence": "asr"})
                sentence_parts.append(txt)
        raw = " ".join(sentence_parts).strip()
        return {
            "mode": "en-asr-only",
            "tokens": tokens,
            "english_sentence": _space_fix(raw),
            "notes": "Direct English ASR (Whisper) triggered by english=True flag."
        }

@app.post("/audio/arrernte-to-english", summary="Upload Arrernte audio and get English output (STRICT glossary-matching; no Whisper fallback)")
async def arrernte_to_english(file: UploadFile = File(...), english: bool = Form(False)):
    """
    Accepts an audio file (mp3/wav/m4a/etc). Returns JSON with best English guess using ONLY the glossary audio.
    Fails with 501 if required libraries are missing.
    """
    # Save upload to temp
    try:
        suffix = Path(file.filename or "audio").suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
    except Exception as e:
        raise HTTPException(400, f"Failed to read upload: {e}")

    try:
        return JSONResponse(_english_audio_to_english_text(tmp_path) if english else _arrernte_to_english_via_glossary_hybrid(tmp_path))
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
