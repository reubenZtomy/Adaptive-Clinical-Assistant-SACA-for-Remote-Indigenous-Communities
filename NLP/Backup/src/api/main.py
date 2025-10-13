# src/api/main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from faster_whisper import WhisperModel
from src.nlu.simple_nlu import analyze
from src.pipeline.translate import GlossaryMT, normalize_lang
from pathlib import Path
import os, tempfile, warnings

# --- Suppress deprecated pkg_resources warnings from ctranslate2 ---
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

# ---------- Config ----------
MODEL_SIZE = os.getenv("MODEL_SIZE", "small")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float16")
DEVICE = os.getenv("DEVICE", "cuda")

# Build the correct absolute glossary path dynamically
BASE_DIR = Path(__file__).resolve().parents[2]  # F:\SwinSACA\NLP\API_Endpoints
GLOSSARY_PATH = BASE_DIR / "Glossary" / "arrernte_audio.csv"

# Create output directory if needed
OUT_DIR = BASE_DIR / "data" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Data Models ----------
class NLUIn(BaseModel):
    text: str
    lang: str = "en"

class TranslateIn(BaseModel):
    text: str
    src_lang: str = "en"
    tgt_lang: str = "pjt"

# ---------- App ----------
app = FastAPI(title="SwinSACA ASR + MT + NLU")

# ---------- Model Initialization ----------
try:
    asr_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
except Exception as e:
    print(f"[WARN] WhisperModel failed to load ({e}), falling back to CPU")
    asr_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

print(f"✅ Glossary loaded from: {GLOSSARY_PATH}")
glossary_mt = GlossaryMT(str(GLOSSARY_PATH))

# ---------- Health ----------
@app.get("/health")
def health():
    sizes = {
        "en->pjt": len(glossary_mt.lex.get("en->pjt", {})),
        "pjt->en": len(glossary_mt.lex.get("pjt->en", {})),
    }
    return {
        "status": "ok",
        "device": DEVICE,
        "model": MODEL_SIZE,
        "compute_type": COMPUTE_TYPE,
        "glossary_sizes": sizes,
        "glossary_path": str(GLOSSARY_PATH)
    }

# ---------- ASR ----------
@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), lang: str | None = Form(default=None)):
    suffix = os.path.splitext(audio.filename)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        segments, info = asr_model.transcribe(tmp_path, language=lang, vad_filter=True, beam_size=5, best_of=5)
        parts = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text} for s in segments]
        text = "".join(s.text for s in segments).strip()
        return JSONResponse({
            "detected_language": info.language,
            "language_probability": round(float(info.language_probability), 3),
            "text": text,
            "segments": parts
        })
    finally:
        os.remove(tmp_path)

# ---------- Translate ----------
@app.post("/translate_text")
def translate_text(body: TranslateIn):
    translated = glossary_mt.translate(body.text, body.src_lang, body.tgt_lang)
    return {
        "text": body.text,
        "src_lang": body.src_lang,
        "tgt_lang": body.tgt_lang,
        "translation": translated
    }

# ---------- Reload Glossary ----------
@app.post("/reload_glossary")
def reload_glossary():
    global glossary_mt
    glossary_mt = GlossaryMT(str(GLOSSARY_PATH))
    sizes = {
        "en->pjt": len(glossary_mt.lex.get("en->pjt", {})),
        "pjt->en": len(glossary_mt.lex.get("pjt->en", {})),
    }
    return {"reloaded": True, "sizes": sizes}

# ---------- NLU ----------
@app.post("/nlu_text")
def nlu_text(body: NLUIn):
    text_en = body.text if body.lang.startswith("en") else glossary_mt.translate(body.text, "pjt", "en")
    result = analyze(text_en)
    return {
        "input_text": body.text,
        "lang": body.lang,
        "normalized_text_en": text_en,
        "nlu": result
    }
