# NLP/API_Endpoints/app.py  — clean, no docstring YAML

import os, csv, re, tempfile, threading, webbrowser, requests, uuid, sys
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flasgger import Swagger

# ensure we can import sibling packages even if launched from elsewhere
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# --- Chatbot core (now in API_Endpoints/Chatbot/) ---
from Chatbot.chat import route_message, reset_state, predict_tag, bot_name, dialog_state

# Optional heavy deps (installed via pip)
from faster_whisper import WhisperModel
from pydub import AudioSegment
import pyttsx3
from rapidfuzz import process, fuzz, distance

BASE_DIR = HERE
CSV_PATH = os.path.join(BASE_DIR, "Glossary", "arrernte_audio.csv")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base.en")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"]}}, supports_credentials=True)

# ---- Minimal Swagger template (no """ strings) ----
SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "SwinSACA API",
        "version": "1.0.0",
        "description": "Chat + translation + speech endpoints for SwinSACA"
    },
    "basePath": "/",
    "schemes": ["http"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "paths": {
        "/health": {
            "get": {
                "tags": ["System"],
                "summary": "Health check",
                "responses": {
                    "200": {"description": "OK"}
                }
            }
        },

        "/chat": {
            "post": {
                "tags": ["Chat"],
                "summary": "Chat with the SwinSACA bot",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "required": ["message"],
                        "properties": {
                            "message": {"type": "string", "example": "I have a headache"},
                            "reset": {"type": "boolean", "example": False},
                            "_context": {
                                "type": "object",
                                "properties": {
                                    "language": {"type": "string", "example": "arrernte | english | arr+english"},
                                    "mode": {"type": "string", "example": "text | voice"}
                                }
                            }
                        }
                    }
                }],
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"description": "Missing input"}
                }
            }
        },

        "/api/translate_to_arrernte": {
            "post": {
                "tags": ["Translate"],
                "summary": "Translate English → Arrernte (glossary mix)",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "required": ["text"],
                        "properties": {
                            "text": {"type": "string", "example": "Please sit down and relax."}
                        }
                    }
                }],
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"description": "Missing input"}
                }
            }
        },

        "/api/translate_to_english": {
            "post": {
                "tags": ["Translate"],
                "summary": "Translate Arrernte → English (with fuzzy match)",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "required": ["text"],
                        "properties": {
                            "text": {"type": "string", "example": "arrernte-ketye nhenhe angkentye"}
                        }
                    }
                }],
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"description": "Missing input"}
                }
            }
        },

        "/api/transcribe": {
            "post": {
                "tags": ["Audio"],
                "summary": "Transcribe audio with Whisper (English)",
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {
                        "in": "formData",
                        "name": "audio",
                        "type": "file",
                        "required": True,
                        "description": "Audio file (wav/mp3/m4a, etc.)"
                    }
                ],
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"description": "No file"}
                }
            }
        },

        "/api/speak_translated_mixed": {
            "post": {
                "tags": ["Audio"],
                "summary": "Speak mixed (Arrernte clips + TTS) and return audio file",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "required": ["text"],
                        "properties": {
                            "text": {"type": "string", "example": "Please take deep breaths."},
                            "format": {"type": "string", "enum": ["mp3", "wav"], "default": "mp3"},
                            "pause_ms": {"type": "integer", "default": 120}
                        }
                    }
                }],
                "responses": {
                    "200": {
                        "description": "Audio file",
                        "schema": {"type": "string", "format": "binary"}
                    },
                    "400": {"description": "Missing input"}
                },
                "produces": ["audio/mpeg", "audio/wav"]
            }
        },

        "/api/transcribe_arr_to_english": {
            "post": {
                "tags": ["Audio"],
                "summary": "Transcribe Arrernte and translate to English",
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {
                        "in": "formData",
                        "name": "audio",
                        "type": "file",
                        "required": True,
                        "description": "Audio file (wav/mp3/m4a, etc.)"
                    },
                    {
                        "in": "formData",
                        "name": "force_language",
                        "type": "string",
                        "description": "Force language ('auto' | 'en')",
                        "default": "auto"
                    },
                    {
                        "in": "formData",
                        "name": "fuzzy_cutoff",
                        "type": "integer",
                        "description": "RapidFuzz score cutoff (0–100)",
                        "default": 85
                    },
                    {
                        "in": "formData",
                        "name": "max_edit",
                        "type": "integer",
                        "description": "Max Levenshtein distance",
                        "default": 1
                    },
                    {
                        "in": "formData",
                        "name": "english_headword_only",
                        "type": "boolean",
                        "description": "Return headword only",
                        "default": True
                    }
                ],
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"description": "No file"}
                }
            }
        }
    }
}

swagger = Swagger(app, template=SWAGGER_TEMPLATE)

# ---------------- Glossary loading ----------------
EN2ARR = {}
ARR2ENG = {}

def load_csv():
    EN2ARR.clear()
    ARR2ENG.clear()
    if not os.path.exists(CSV_PATH):
        return
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eng_raw = (row.get("english_meaning") or "").strip()
            arr = (row.get("arrernte_word") or "").strip()
            url = (row.get("audio_url") or "").strip()
            if not eng_raw or not arr:
                continue
            primary_eng = eng_raw.split(",")[0].strip()
            eng_head = primary_eng.split()[0] if primary_eng else primary_eng
            ARR2ENG[arr.lower()] = {
                "english": primary_eng,
                "english_head": eng_head,
                "audio_url": url
            }
            # map every token in the english_meaning to the arrernte word
            for token in re.findall(r"[A-Za-z']+", eng_raw.lower()):
                EN2ARR.setdefault(token, {"arrernte": arr, "audio_url": url})

load_csv()

# ---------------- Speech model ----------------
whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

def choose_voice(engine):
    voices = engine.getProperty("voices")
    cand = None
    for v in voices:
        name = (getattr(v, "name", "") or "").lower()
        langs = [str(x).lower() for x in getattr(v, "languages", [])]
        if "en" in "".join(langs) or "english" in name:
            cand = v
            if any(k in name for k in ("zira", "aria", "jenny", "david", "guy")):
                return v
    return cand or (voices[0] if voices else None)

def tts_to_file(text, out_path):
    engine = pyttsx3.init()
    v = choose_voice(engine)
    if v:
        engine.setProperty("voice", v.id)
    engine.save_to_file(text, out_path)
    engine.runAndWait()

def safe_download(url, out_path):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)

def is_word(token):
    return re.fullmatch(r"[A-Za-z']+", token) is not None

def split_with_separators(s):
    parts = re.split(r"(\b[A-Za-z']+\b)", s)
    return [p for p in parts if p != ""]

def export_audio(segments, fmt, out_path):
    joined = AudioSegment.silent(duration=1)
    for seg in segments:
        joined += seg
    joined.export(out_path, format=fmt)

# ---------------- helpers: chatbot state + glossary ----------------
def _copy_state():
    return {
        "active_domain": dialog_state.get("active_domain"),
        "stage": dialog_state.get("stage"),
        "slots": dict(dialog_state.get("slots", {})),
    }

def _apply_arrernte_glossary_to_reply(text: str):
    """Replace words in the *bot reply* using EN2ARR map. Returns (mixed_text, replaced_list)."""
    replaced = []
    if not text or not EN2ARR:
        return text, replaced

    def repl(m):
        w = m.group(0)
        k = w.lower()
        if k in EN2ARR:
            entry = EN2ARR[k]
            replaced.append({
                "english": w,
                "arrernte": entry.get("arrernte", w),
                "audio_url": entry.get("audio_url", "")
            })
            return entry.get("arrernte", w)
        return w

    mixed = re.sub(r"\b[A-Za-z']+\b", repl, text)
    return mixed, replaced

# ---------------- Routes ----------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "SwinSACA Flask API"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_msg_raw = (data.get("message") or "").strip()
    if not user_msg_raw:
        return jsonify({"error": "Provide JSON with 'message'"}), 400

    # Optional: reset dialog flow
    if data.get("reset"):
        reset_state()

    ctx = data.get("_context") or {}
    lang = (request.headers.get("X-Language") or ctx.get("language") or "english").lower()
    mode = (request.headers.get("X-Mode") or ctx.get("mode") or "text").lower()

    # ------------------ Arrernte → English (improved) ------------------
    # Heuristics:
    # - Prefer headword, then normalise sense for medical/triage contexts.
    # - Longest-literal first isn't possible without phrase entries in CSV,
    #   but we still tidy common ambiguous senses.
    # - Skip fuzzy for very short tokens; stronger guard on edit distance.
    MEDICAL_HINTS = {"pain", "headache", "exactly", "where", "location", "chest", "stomach", "back", "side", "left", "right"}

    # Ambiguous single-token senses we want to normalise when the sentence looks medical.
    # These are *output* English sense fixes for common glossary polysemy.
    SENSE_OVERRIDES = {
        # glossary sense → better medical sense
        "rockhole (where water collects)": "where",
        "rockhole": "where",
        "return": "back",
        "cliff": "side",
        "outside": "outside",  # keep, but see further below for 'outside pain' -> 'outer pain' guard
        "left hand": "left",
        "right hand": "right",
        "child who has lost one or both parents": "left",  # common mis-map; prefer 'left' in body-location contexts
    }

    def looks_medical_context(s: str) -> bool:
        s_low = s.lower()
        return any(h in s_low for h in MEDICAL_HINTS)

    def normalise_english_sense(eng: str, full_text_context: str) -> str:
        """
        Fix awkward or polysemous senses for medical triage phrasing.
        """
        if not eng:
            return eng
        base = eng.strip()

        # Drop parenthetical glosses for clarity
        if "(" in base and ")" in base:
            # e.g., "rockhole (where water collects)" → prefer the part in parens or override below
            # keep the shorter side if it reads cleaner
            try:
                before, after = base.split("(", 1)
                inside = after.split(")", 1)[0].strip()
                # If inside looks like a functional gloss ("where ..."), prefer it
                if looks_medical_context(full_text_context) and inside and len(inside.split()) <= 3:
                    base = inside
                else:
                    base = before.strip() or inside or base
            except Exception:
                pass

        # Apply direct overrides when medical
        if looks_medical_context(full_text_context):
            for k, v in SENSE_OVERRIDES.items():
                if base.lower() == k.lower():
                    base = v
                    break

        # Micro cleanups
        # "outside pain" → "outer pain" (reads more natural)
        base = re.sub(r"\boutside pain\b", "outer pain", base, flags=re.I)

        return base

    def postjoin_collocations(words: list) -> list:
        """
        Adjust sequences like ["left", "hand"] -> ["left"] and
        ["right", "hand"] -> ["right"]; also make "left/right side" explicit.
        """
        out = []
        i = 0
        while i < len(words):
            w = words[i]
            nxt = words[i + 1] if i + 1 < len(words) else None

            if nxt and w.lower() in {"left", "right"} and nxt.lower() == "hand":
                out.append(w)  # keep 'left'/'right' only
                i += 2
                continue

            # If we already have 'left'/'right' followed later by 'side', keep "left/right side"
            if nxt and w.lower() in {"left", "right"} and nxt.lower() == "side":
                out.append(f"{w.lower()} side")
                i += 2
                continue

            out.append(w)
            i += 1
        return out

    def translate_arr_to_english(
        text: str,
        english_headword_only: bool = True,
        fuzzy_cutoff: int = 88,   # slightly stricter than before
        max_edit: int = 1,
        min_len_for_fuzzy: int = 4
    ) -> (str, list):
        """
        Returns (translated_text, replaced_list).
        replaced_list items: {"arrernte": <w>, "english": <e>, "audio_url": <url>}
        """
        if not text:
            return text, []

        ensure_arr_keys()  # keep ARR_KEYS in sync
        replaced = []
        tokens_out = []

        # Split into words + separators, allowing diacritics/hyphens/apostrophes
        parts = re.split(r"(\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\b)", text)

        for p in parts:
            # Keep non-word separators as-is
            if not p or not re.fullmatch(r"\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\b", p):
                tokens_out.append(p)
                continue

            w = p
            k = w.lower()

            # Skip fuzzy on very short tokens to avoid wild matches
            allow_fuzzy = len(k) >= min_len_for_fuzzy

            # Exact match first
            if k in ARR2ENG:
                e = ARR2ENG[k]
                eng = e["english_head"] if english_headword_only else e["english"]
                eng = normalise_english_sense(eng, text)
                tokens_out.append(eng)
                replaced.append({"arrernte": w, "english": eng, "audio_url": e.get("audio_url", "")})
                continue

            # Fuzzy match if allowed
            if allow_fuzzy and ARR_KEYS:
                match = process.extractOne(k, ARR_KEYS, scorer=fuzz.WRatio, score_cutoff=fuzzy_cutoff)
                if match:
                    cand, score, _ = match
                    try:
                        if distance.Levenshtein.distance(k, cand) <= max_edit:
                            e = ARR2ENG[cand]
                            eng = e["english_head"] if english_headword_only else e["english"]
                            eng = normalise_english_sense(eng, text)
                            tokens_out.append(eng)
                            replaced.append({"arrernte": w, "english": eng, "audio_url": e.get("audio_url", "")})
                            continue
                    except Exception:
                        e = ARR2ENG[cand]
                        eng = e["english_head"] if english_headword_only else e["english"]
                        eng = normalise_english_sense(eng, text)
                        tokens_out.append(eng)
                        replaced.append({"arrernte": w, "english": eng, "audio_url": e.get("audio_url", "")})
                        continue

            # No mapping → keep original token
            tokens_out.append(w)

        # SECOND PASS: tidy collocations like "left hand" → "left"
        # Do this only on *word* chunks; leave punctuation intact.
        # We reconstruct while tracking word vs separator segments.
        rebuilt = []
        word_buf = []
        for seg in tokens_out:
            if seg and re.fullmatch(r"\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\b", seg):
                word_buf.append(seg)
            else:
                if word_buf:
                    word_buf = postjoin_collocations(word_buf)
                    rebuilt.append(" ".join(word_buf))
                    word_buf = []
                rebuilt.append(seg)
        if word_buf:
            word_buf = postjoin_collocations(word_buf)
            rebuilt.append(" ".join(word_buf))

        return "".join(rebuilt), replaced

    # ---------- 1) Pre-translate user input if client says it's Arrernte ----------
    user_msg_for_bot = user_msg_raw
    input_replaced = []
    if lang == "arrernte":
        user_msg_for_bot, input_replaced = translate_arr_to_english(
            user_msg_raw,
            english_headword_only=True,
            fuzzy_cutoff=88,
            max_edit=1,
            min_len_for_fuzzy=4
        )

    # ---------- 2) Route message (in English if we just translated) ----------
    bot_reply_english = route_message(user_msg_for_bot)
    state_copy = _copy_state()

    # ---------- 3) Post-process bot reply to Arrernte if client requested Arrernte ----------
    replaced_out = []
    final_reply = bot_reply_english
    if lang == "arrernte":
        final_reply, replaced_out = _apply_arrernte_glossary_to_reply(bot_reply_english)

    return jsonify({
        "reply": final_reply,
        "context": {"language": lang, "mode": mode},
        "replaced_words": replaced_out,   # replacements made in BOT reply (EN → Arr)
        "state": state_copy,
        "bot": bot_name,
        # Optional debug to see input-side translation; uncomment for development:
        # "debug_input": {
        #     "original": user_msg_raw,
        #     "translated_to_english": user_msg_for_bot if lang == "arrernte" else None,
        #     "replaced_from_input": input_replaced if lang == "arrernte" else []
        # }
    })


@app.route("/api/translate_to_arrernte", methods=["POST"])
def translate_to_arrernte():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Provide JSON with 'text'"}), 400
    replaced = []
    def repl(m):
        w = m.group(0)
        k = w.lower()
        if k in EN2ARR:
            entry = EN2ARR[k]
            replaced.append({"english": w, "arrernte": entry["arrernte"], "audio_url": entry["audio_url"]})
            return entry["arrernte"]
        return w
    translated = re.sub(r"\b[A-Za-z']+\b", repl, text)
    return jsonify({"original_text": text, "translated_text": translated, "replaced_words": replaced})

@app.route("/api/translate_to_english", methods=["POST"])
def translate_to_english():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Provide JSON with 'text'"}), 400
    replaced = []
    def repl(m):
        w = m.group(0)
        k = w.lower()
        if k in ARR2ENG:
            entry = ARR2ENG[k]
            replaced.append({"arrernte": w, "english": entry["english"], "audio_url": entry["audio_url"]})
            return entry["english"]
        return w
    translated = re.sub(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", repl, text)
    return jsonify({"original_text": text, "translated_text": translated, "replaced_words": replaced})

@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No 'audio' file provided"}), 400
    f = request.files["audio"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    suffix = os.path.splitext(f.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        path = tmp.name
    try:
        segments, info = whisper_model.transcribe(path, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        return jsonify({"text": text})
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

@app.route("/api/speak_translated_mixed", methods=["POST"])
def speak_translated_mixed():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Provide JSON with 'text'"}), 400
    fmt = (data.get("format") or "mp3").lower()
    pause_ms = int(data.get("pause_ms", 120))

    def is_word(token): return re.fullmatch(r"[A-Za-z']+", token) is not None
    def split_with_separators(s): return [p for p in re.split(r"(\b[A-Za-z']+\b)", s) if p != ""]

    parts = split_with_separators(text)
    audio_segments = []
    tmpdir = tempfile.mkdtemp(prefix="mix_")
    i = 0
    while i < len(parts):
        token = parts[i]
        if is_word(token) and token.lower() in EN2ARR:
            entry = EN2ARR[token.lower()]
            url = entry.get("audio_url") or ""
            if not url:
                audio_segments.append(AudioSegment.silent(duration=pause_ms))
            else:
                tmpf = os.path.join(tmpdir, f"arr_{i}_{uuid.uuid4().hex}.mp3")
                safe_download(url, tmpf)
                seg = AudioSegment.from_file(tmpf)
                audio_segments.append(seg)
                audio_segments.append(AudioSegment.silent(duration=pause_ms))
            i += 1
            continue
        if is_word(token):
            j = i
            chunk_words = []
            while j < len(parts) and is_word(parts[j]) and parts[j].lower() not in EN2ARR:
                chunk_words.append(parts[j])
                j += 1
            phrase = " ".join(chunk_words)
            tfile = os.path.join(tmpdir, f"tts_{i}_{uuid.uuid4().hex}.wav")
            tts_to_file(phrase, tfile)
            seg = AudioSegment.from_file(tfile)
            audio_segments.append(seg)
            audio_segments.append(AudioSegment.silent(duration=pause_ms))
            i = j
            continue
        i += 1
    if not audio_segments:
        tfile = os.path.join(tmpdir, f"tts_all_{uuid.uuid4().hex}.wav")
        tts_to_file(text, tfile)
        audio_segments.append(AudioSegment.from_file(tfile))
    out_path = os.path.join(tmpdir, f"output.{fmt}")
    export_audio(audio_segments, fmt, out_path)
    return send_file(out_path, as_attachment=True, download_name=f"mixed.{fmt}",
                     mimetype="audio/mpeg" if fmt == "mp3" else "audio/wav")

ARR_KEYS = None

def ensure_arr_keys():
    global ARR_KEYS
    if ARR_KEYS is None or len(ARR_KEYS) != len(ARR2ENG):
        ARR_KEYS = list(ARR2ENG.keys())

@app.route("/api/transcribe_arr_to_english", methods=["POST"])
def transcribe_arr_to_english():
    if "audio" not in request.files:
        return jsonify({"error": "No 'audio' file provided"}), 400
    f = request.files["audio"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    force_language = (request.form.get("force_language") or "auto").lower()
    try:
        fuzzy_cutoff = int(request.form.get("fuzzy_cutoff", 85))
    except ValueError:
        fuzzy_cutoff = 85
    try:
        max_edit = int(request.form.get("max_edit", 1))
    except ValueError:
        max_edit = 1
    english_headword_only = (request.form.get("english_headword_only", "true").lower() in ["1","true","yes","y"])

    suffix = os.path.splitext(f.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        path = tmp.name

    try:
        if force_language == "en":
            segments, info = whisper_model.transcribe(path, language="en")
            lang = "en"
            lang_prob = 1.0
        else:
            segments, info = whisper_model.transcribe(path)
            lang = getattr(info, "language", "auto")
            lang_prob = getattr(info, "language_probability", 0.0)

        text = " ".join(s.text.strip() for s in segments).strip()

        ensure_arr_keys()
        allow_fuzzy = not (lang == "en" and lang_prob >= 0.70)

        parts = re.split(r"(\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\b)", text)
        replaced = []
        out = []

        for p in parts:
            if not p or not re.fullmatch(r"\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\b", p):
                out.append(p)
                continue
            w = p
            k = w.lower()

            if k in ARR2ENG:
                e = ARR2ENG[k]
                out.append(e["english_head"] if english_headword_only else e["english"])
                replaced.append({"arrernte": w, "english": e["english"], "audio_url": e["audio_url"]})
                continue

            if allow_fuzzy and ARR_KEYS:
                match = process.extractOne(k, ARR_KEYS, scorer=fuzz.WRatio, score_cutoff=fuzzy_cutoff)
                if match:
                    cand, score, _ = match
                    if distance.Levenshtein.distance(k, cand) <= max_edit:
                        e = ARR2ENG[cand]
                        out.append(e["english_head"] if english_headword_only else e["english"])
                        replaced.append({"arrernte": w, "english": e["english"], "audio_url": e["audio_url"]})
                        continue

            out.append(w)

        translated = "".join(out)
        return jsonify({
            "raw_transcription": text,
            "translated_text": translated,
            "replaced_words": replaced,
            "language": lang,
            "language_probability": lang_prob
        })
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

def open_docs():
    try:
        webbrowser.open_new("http://localhost:5000/apidocs/")
    except Exception:
        pass

if __name__ == "__main__":
    threading.Timer(1.0, open_docs).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
