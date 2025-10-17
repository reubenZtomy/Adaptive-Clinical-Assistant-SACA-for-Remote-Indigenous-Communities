from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from werkzeug.datastructures import FileStorage
from dotenv import load_dotenv
import os
import csv
import re
import tempfile
import threading
import webbrowser
import requests
import uuid
import sys
import base64
import io
import joblib
import numpy as np
import importlib.util
from pathlib import Path

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///swinsaca.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-string')

# --- Configure external model endpoints here ---
ML1_URL = "http://localhost:5000/api/ml1/predict"   # kept for reference/logging
ML2_URL = "http://localhost:5000/api/ml2/predict"   # kept for reference/logging
FUSION_URL = "http://localhost:5000/api/fusion/compare"  # << updated

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173').split(',')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# More permissive CORS for development
CORS(app, 
     resources={r"/*": {"origins": "*"}},  # Allow all origins for development
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Language", "X-Mode", "Accept", "Origin", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])

# Initialize API with Swagger
api = Api(
    app,
    version='1.0',
    title='SwinSACA API',
    description='AI-guided medical triage API with authentication and chatbot functionality',
    doc='/api/swagger/',
    prefix='/api'
)

# Create models with the database instance
import models
User = models.create_models(db)
models.User = User
models.db = db

# Import routes after setting db
from routes import auth_ns

# Register namespaces
api.add_namespace(auth_ns, path='/auth')

# --- Chatbot core imports ---
try:
    from Chatbot.chat import route_message, reset_state, predict_tag, bot_name, dialog_state
except ImportError:
    # Fallback if running from different directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Chatbot'))
    from chat import route_message, reset_state, predict_tag, bot_name, dialog_state

# Optional heavy deps (installed via pip)
try:
    from faster_whisper import WhisperModel
    from pydub import AudioSegment
    import pyttsx3
    from rapidfuzz import process, fuzz, distance
    HEAVY_DEPS_AVAILABLE = True
    print("[SUCCESS] All heavy dependencies loaded successfully!")
    print("   - faster_whisper: OK")
    print("   - pydub: OK") 
    print("   - pyttsx3: OK")
    print("   - rapidfuzz: OK")
except ImportError as e:
    HEAVY_DEPS_AVAILABLE = False
    print("[ERROR] Some optional dependencies not available. Audio features will be limited.")
    print(f"   Import error: {str(e)}")
    print("   Please install missing dependencies with: pip install faster-whisper pydub pyttsx3 rapidfuzz")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Glossary", "arrernte_audio.csv")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base.en")

# Flask-RESTx will automatically generate Swagger documentation

# Create namespaces for API organization
chat_ns = api.namespace('chat', description='Chat and conversation endpoints')
translate_ns = api.namespace('translate', description='Translation endpoints')
ml2_ns = api.namespace('ml2', description='ML Model-2 prediction endpoints')
ml1_ns = api.namespace('ml1', description='ML Model-1 triage endpoints')
fusion_ns = api.namespace('fusion', description='Model fusion endpoints')

# Define models for request/response documentation
chat_request_model = api.model('ChatRequest', {
    'message': fields.String(required=True, description='User message to the chatbot', example='I have a headache'),
    'reset': fields.Boolean(description='Reset dialog state', example=False),
    '_context': fields.Raw(description='Context information', example={'language': 'english', 'mode': 'text'})
})

chat_response_model = api.model('ChatResponse', {
    'reply': fields.String(description='Bot response'),
    'transcribed_text': fields.String(description='Transcribed text from audio input (voice mode only)'),
    'normalized_text': fields.String(description='Normalized text sent to chatbot (voice mode only)'),
    'context': fields.Raw(description='Context information'),
    'replaced_words': fields.List(fields.Raw, description='Words replaced in translation'),
    'state': fields.Raw(description='Dialog state'),
    'bot': fields.String(description='Bot name'),
    'is_final_message': fields.Boolean(description='Whether this is a final message for disease prediction'),
    'disease_prediction': fields.Raw(description='Disease prediction results (if final message)'),
    'audio_url': fields.String(description='URL to the audio response (voice mode only)')
})

translate_request_model = api.model('TranslateRequest', {
    'text': fields.String(required=True, description='Text to translate', example='I have a headache')
})

translate_response_model = api.model('TranslateResponse', {
    'original_text': fields.String(description='Original text'),
    'translated_text': fields.String(description='Translated text'),
    'replaced_words': fields.List(fields.Raw, description='Words that were replaced')
})

# ---------------- ML Model-1: Triage API ----------------
ML1_DIR = os.path.join(BASE_DIR, "Ml model-1")
ML1_TRIAGE_MODULE_PATH = os.path.join(ML1_DIR, "triage_model.py")

_ml1 = None

def _load_ml1_module():
    global _ml1
    if _ml1 is not None:
        return _ml1
    if not os.path.exists(ML1_TRIAGE_MODULE_PATH):
        raise FileNotFoundError(f"triage_model.py not found at {ML1_TRIAGE_MODULE_PATH}")
    spec = importlib.util.spec_from_file_location("triage_model", ML1_TRIAGE_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _ml1 = mod
    return _ml1

ml1_predict_request_model = api.model('ML1PredictRequest', {
    'input': fields.String(required=True, description='Free-form symptom description', example='I have chest pain and shortness of breath'),
    'topk': fields.Integer(description='Top-k diseases to return (default 3)', example=3)
})

ml1_disease_item_model = api.model('ML1DiseaseItem', {
    'disease': fields.String(description='Disease label'),
    'p': fields.Float(description='Probability (0-1)')
})

ml1_predict_response_model = api.model('ML1PredictResponse', {
    'severity': fields.String(description='Predicted severity'),
    'confidence': fields.Float(description='Severity confidence (0-1)'),
    'probs': fields.List(fields.Float, description='Severity probabilities (ordered as in model config)'),
    'disease_topk': fields.List(fields.Nested(ml1_disease_item_model), description='Top-k diseases if available')
})

ml1_meta_response_model = api.model('ML1MetaResponse', {
    'artifact_dir': fields.String(description='Artifact directory'),
    'has_disease_model': fields.Boolean(description='Whether disease model is available'),
    'severity_labels': fields.List(fields.String, description='Severity labels'),
    'disease_labels': fields.List(fields.String, description='Disease labels (if available)')
})

# ---------------- Fusion: Compare ML1 and ML2 ----------------
fusion_request_model = api.model('FusionRequest', {
    'input': fields.String(required=True, description='Free-form symptom description', example='Headache and nausea for two days'),
    'topk': fields.Integer(description='Top-k diseases to return from ML1 (default 3)')
})

fusion_final_model = api.model('FusionFinal', {
    'severity': fields.String(description='Final severity (from ML1)'),
    'disease_label': fields.String(description='Chosen disease label'),
    'probability': fields.Float(description='Chosen label probability'),
    'source': fields.String(description="'ml1' or 'ml2'"),
    'policy': fields.String(description='Decision policy used')
})

fusion_response_model = api.model('FusionResponse', {
    'input': fields.String(description='Echoed input'),
    'ml1': fields.Raw(description='Raw ML1 result'),
    'ml2': fields.Raw(description='Raw ML2 result'),
    'final': fields.Nested(fusion_final_model, description='Selected final result')
})

# ---------------- ML Model-2: Prediction API ----------------
# Uses components under 'Ml model-2/model_components': vectorizer, kmeans, q_table, label_encoder
ML2_DIR = os.path.join(BASE_DIR, "Ml model-2")
ML2_COMPONENTS_DIR = os.path.join(ML2_DIR, "model_components")
ML2_VECTORIZER_PATH = os.path.join(ML2_COMPONENTS_DIR, "vectorizer.pkl")
ML2_KMEANS_PATH = os.path.join(ML2_COMPONENTS_DIR, "kmeans.pkl")
ML2_QTABLE_PATH = os.path.join(ML2_COMPONENTS_DIR, "q_table.npy")
ML2_LABEL_ENCODER_PATH = os.path.join(ML2_COMPONENTS_DIR, "label_encoder.pkl")

ml2_predict_request_model = api.model('ML2PredictRequest', {
    'input': fields.String(required=True, description='Free-form symptom description string', example='I have severe headache and nausea for two days')
})

ml2_top_item_model = api.model('ML2TopItem', {
    'label': fields.String(description='Predicted label'),
    'probability': fields.Float(description='Softmax score over Q-values (0-1)')
})

ml2_predict_response_model = api.model('ML2PredictResponse', {
    'predicted_label': fields.String(description='Top predicted label'),
    'probability': fields.Float(description='Top softmax score (0-1)'),
    'top': fields.List(fields.Nested(ml2_top_item_model), description='Top 3 predictions')
})

_ml2_vectorizer = None
_ml2_kmeans = None
_ml2_qtable = None
_ml2_label_encoder = None

def _ml2_get_components():
    global _ml2_vectorizer, _ml2_kmeans, _ml2_qtable, _ml2_label_encoder
    if all(x is not None for x in (_ml2_vectorizer, _ml2_kmeans, _ml2_qtable, _ml2_label_encoder)):
        return _ml2_vectorizer, _ml2_kmeans, _ml2_qtable, _ml2_label_encoder
    missing = []
    for p in [ML2_VECTORIZER_PATH, ML2_KMEANS_PATH, ML2_QTABLE_PATH, ML2_LABEL_ENCODER_PATH]:
        if not os.path.exists(p):
            missing.append(p)
    if missing:
        raise FileNotFoundError(f"Missing ML2 components: {missing}")
    _ml2_vectorizer = joblib.load(ML2_VECTORIZER_PATH)
    _ml2_kmeans = joblib.load(ML2_KMEANS_PATH)
    _ml2_qtable = np.load(ML2_QTABLE_PATH)
    _ml2_label_encoder = joblib.load(ML2_LABEL_ENCODER_PATH)
    return _ml2_vectorizer, _ml2_kmeans, _ml2_qtable, _ml2_label_encoder

@ml2_ns.route('/predict')
class ML2Predict(Resource):
    @ml2_ns.expect(ml2_predict_request_model)
    @ml2_ns.marshal_with(ml2_predict_response_model)
    def post(self):
        data = request.get_json(silent=True) or {}
        # Accept either 'input' or 'text'
        input_text = (data.get('input') or data.get('text') or '').strip()
        if not input_text:
            api.abort(400, "Provide JSON with 'input' or 'text'")

        try:
            vectorizer, kmeans, q_table, label_encoder = _ml2_get_components()
        except FileNotFoundError as e:
            api.abort(500, str(e))

        try:
            X = vectorizer.transform([input_text])
            state = int(kmeans.predict(X)[0])
            q_values = q_table[state]
            
            # Fix dimension mismatch: Q-table has more actions than label encoder classes
            # Truncate Q-values to match label encoder classes
            num_classes = len(label_encoder.classes_)
            if len(q_values) > num_classes:
                q_values = q_values[:num_classes]
            
            # Softmax over Q-values for relative scores
            q_shift = q_values - float(np.max(q_values))
            exp_q = np.exp(q_shift)
            probs = exp_q / float(np.sum(exp_q))
            best_idx = int(np.argmax(probs))
            top_indices = list(np.argsort(-probs)[:3])
            labels = label_encoder.inverse_transform(np.arange(len(probs)))
        except Exception as e:
            api.abort(500, f"Model inference failed: {str(e)}")

        return {
            'predicted_label': str(labels[best_idx]),
            'probability': float(probs[best_idx]),
            'top': [
                {'label': str(labels[i]), 'probability': float(probs[i])}
                for i in top_indices
            ]
        }

@ml1_ns.route('/predict')
class ML1Predict(Resource):
    @ml1_ns.expect(ml1_predict_request_model)
    @ml1_ns.marshal_with(ml1_predict_response_model)
    def post(self):
        data = request.get_json(silent=True) or {}
        text = (data.get('input') or data.get('text') or '').strip()
        topk = data.get('topk')
        if not text:
            api.abort(400, "Provide JSON with 'input' or 'text'")
        try:
            mod = _load_ml1_module()
            kwargs = {}
            if isinstance(topk, int) and topk > 0:
                kwargs['topk_diseases'] = topk
            result = mod.triage_predict(text, **kwargs)
            return result
        except FileNotFoundError as e:
            api.abort(500, str(e))
        except Exception as e:
            api.abort(500, f"ML1 inference failed: {str(e)}")

@ml1_ns.route('/meta')
class ML1Meta(Resource):
    @ml1_ns.marshal_with(ml1_meta_response_model)
    def get(self):
        try:
            mod = _load_ml1_module()
            meta = mod.triage_meta()
            return meta
        except FileNotFoundError as e:
            api.abort(500, str(e))
        except Exception as e:
            api.abort(500, f"ML1 meta failed: {str(e)}")

def _ml2_predict_from_text_freeform(text: str):
    vectorizer, kmeans, q_table, label_encoder = _ml2_get_components()
    X = vectorizer.transform([text])
    state = int(kmeans.predict(X)[0])
    q_values = q_table[state]
    
    # Fix dimension mismatch: Q-table has more actions than label encoder classes
    # Truncate Q-values to match label encoder classes
    num_classes = len(label_encoder.classes_)
    if len(q_values) > num_classes:
        q_values = q_values[:num_classes]
    
    q_shift = q_values - float(np.max(q_values))
    exp_q = np.exp(q_shift)
    probs = exp_q / float(np.sum(exp_q))
    best_idx = int(np.argmax(probs))
    labels = label_encoder.inverse_transform(np.arange(len(probs)))
    top_indices = list(np.argsort(-probs)[:3])
    return {
        'predicted_label': str(labels[best_idx]),
        'probability': float(probs[best_idx]),
        'top': [
            {'label': str(labels[i]), 'probability': float(probs[i])}
            for i in top_indices
        ]
    }

@fusion_ns.route('/compare')
class FusionCompare(Resource):
    @fusion_ns.expect(fusion_request_model)
    @fusion_ns.marshal_with(fusion_response_model)
    def post(self):
        data = request.get_json(silent=True) or {}
        text = (data.get('input') or data.get('text') or '').strip()
        topk = data.get('topk')
        if not text:
            api.abort(400, "Provide JSON with 'input' or 'text'")

        # Run ML1
        try:
            mod = _load_ml1_module()
            kwargs = {}
            if isinstance(topk, int) and topk > 0:
                kwargs['topk_diseases'] = topk
            ml1_res = mod.triage_predict(text, **kwargs)
        except Exception as e:
            api.abort(500, f"ML1 failed: {str(e)}")

        # Run ML2
        try:
            ml2_res = _ml2_predict_from_text_freeform(text)
        except Exception as e:
            api.abort(500, f"ML2 failed: {str(e)}")

        # Decision policy:
        # - Severity comes from ML1 (it knows severity)
        # - Disease label: compare ML1 top-1 (if available) vs ML2 top-1 by probability
        policy = "ml1-severity + maxprob(disease from ml1 vs ml2)"
        ml1_top1 = None
        if isinstance(ml1_res, dict) and isinstance(ml1_res.get('disease_topk'), list) and len(ml1_res['disease_topk']) > 0:
            d0 = ml1_res['disease_topk'][0]
            ml1_top1 = {'label': d0.get('disease'), 'probability': d0.get('p', 0.0)}

        ml2_top1 = None
        if isinstance(ml2_res, dict) and isinstance(ml2_res.get('top'), list) and len(ml2_res['top']) > 0:
            d0 = ml2_res['top'][0]
            ml2_top1 = {'label': d0.get('label'), 'probability': d0.get('probability', 0.0)}

        chosen = None
        if ml1_top1 and ml2_top1:
            chosen = ml1_top1 if ml1_top1['probability'] >= ml2_top1['probability'] else ml2_top1
            chosen['source'] = 'ml1' if chosen is ml1_top1 else 'ml2'
        elif ml1_top1:
            chosen = {**ml1_top1, 'source': 'ml1'}
        elif ml2_top1:
            chosen = {**ml2_top1, 'source': 'ml2'}
        else:
            chosen = {'label': None, 'probability': 0.0, 'source': 'none'}

        final = {
            'severity': ml1_res.get('severity'),
            'disease_label': chosen.get('label'),
            'probability': chosen.get('probability'),
            'source': chosen.get('source'),
            'policy': policy
        }

        return {
            'input': text,
            'ml1': ml1_res,
            'ml2': ml2_res,
            'final': final
        }


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
if HEAVY_DEPS_AVAILABLE:
    print(f"[INFO] Loading Whisper model: {WHISPER_MODEL}")
    try:
        whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[SUCCESS] Whisper model loaded successfully!")
        print(f"   Model: {WHISPER_MODEL}")
        print(f"   Device: cpu")
        print(f"   Compute type: int8")
    except Exception as e:
        print(f"[ERROR] Failed to load Whisper model: {str(e)}")
        import traceback
        traceback.print_exc()
        whisper_model = None
else:
    print("[WARNING] Heavy dependencies not available, Whisper model not loaded")
    whisper_model = None

def normalize_numbers_in_text(text: str) -> str:
    """Normalize numbers in text for better processing."""
    if not text:
        return text
    
    # Simple number normalization - you can expand this as needed
    import re
    # Convert common number words to digits
    number_map = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'
    }
    
    normalized = text.lower()
    for word, digit in number_map.items():
        normalized = normalized.replace(word, digit)
    
    return normalized

def transcribe_audio_file(audio_file) -> str:
    """Transcribe audio file to text using Whisper."""
    if not HEAVY_DEPS_AVAILABLE or whisper_model is None:
        return "Audio transcription not available"
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            audio_file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Transcribe using Whisper
        segments, info = whisper_model.transcribe(tmp_path, beam_size=5)
        
        # Combine all segments
        transcribed_text = ""
        for segment in segments:
            transcribed_text += segment.text + " "
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return transcribed_text.strip()
    except Exception as e:
        print(f"[ERROR] Audio transcription failed: {str(e)}")
        return "Transcription failed"

def text_to_speech(text: str, language: str = "en") -> str:
    """Convert text to speech and return audio URL."""
    if not HEAVY_DEPS_AVAILABLE or not text:
        return None
    
    try:
        # Generate unique filename
        audio_id = str(uuid.uuid4()).replace('-', '')
        audio_filename = f"tts_{audio_id}.wav"
        audio_path = os.path.join(BASE_DIR, "static", "audio", audio_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Generate TTS audio
        tts_to_file(text, audio_path)
        
        # Return URL path
        return f"/static/audio/{audio_filename}"
    except Exception as e:
        print(f"[ERROR] TTS generation failed: {str(e)}")
        return None

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
    if not HEAVY_DEPS_AVAILABLE:
        raise ImportError("pyttsx3 not available")
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
    if not HEAVY_DEPS_AVAILABLE:
        raise ImportError("pydub not available")
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

# ---------------- Disease Prediction Function ----------------
def predict_disease_from_conversation(final_user_message, dialog_state, conversation_history=None):
    """
    Predict disease based on conversation history and final user message.
    
    This function calls ML1, ML2, and Fusion APIs to get disease predictions.
    
    Args:
        final_user_message (str): The final message from the user
        dialog_state (dict): The current dialog state with collected information
        conversation_history (list): Complete conversation history with user and assistant messages
    
    Returns:
        dict: Disease prediction results from the fusion API
    """
    try:
        # Build summary from conversation history, dialog state, and final message
        # Create a temporary instance to call the method
        temp_instance = Chat()
        summary = temp_instance._build_summary_for_models(dialog_state, final_user_message, conversation_history)
        
        print(f"[DEBUG] Calling ML APIs with summary: {summary}")
        
        # Call ML1 API
        ml1_url = "http://localhost:5000/api/ml1/predict"
        ml1_payload = {"input": summary, "topk": 3}
        
        print(f"[DEBUG] Calling ML1 API: {ml1_url}")
        ml1_response = requests.post(ml1_url, json=ml1_payload, timeout=30)
        ml1_result = ml1_response.json() if ml1_response.status_code == 200 else None
        
        if not ml1_result:
            print(f"[ERROR] ML1 API failed: {ml1_response.status_code}")
            return {"error": "ML1 API failed", "ml1_status": ml1_response.status_code}
        
        print(f"[DEBUG] ML1 result: {ml1_result}")
        
        # Call ML2 API
        ml2_url = "http://localhost:5000/api/ml2/predict"
        ml2_payload = {"input": summary}
        
        print(f"[DEBUG] Calling ML2 API: {ml2_url}")
        ml2_response = requests.post(ml2_url, json=ml2_payload, timeout=30)
        ml2_result = ml2_response.json() if ml2_response.status_code == 200 else None
        
        if not ml2_result:
            print(f"[ERROR] ML2 API failed: {ml2_response.status_code}")
            return {"error": "ML2 API failed", "ml2_status": ml2_response.status_code}
        
        print(f"[DEBUG] ML2 result: {ml2_result}")
        
        # Call Fusion API
        fusion_url = "http://localhost:5000/api/fusion/compare"
        fusion_payload = {"input": summary, "topk": 3}
        
        print(f"[DEBUG] Calling Fusion API: {fusion_url}")
        fusion_response = requests.post(fusion_url, json=fusion_payload, timeout=30)
        fusion_result = fusion_response.json() if fusion_response.status_code == 200 else None
        
        if not fusion_result:
            print(f"[ERROR] Fusion API failed: {fusion_response.status_code}")
            return {"error": "Fusion API failed", "fusion_status": fusion_response.status_code}
        
        print(f"[DEBUG] Fusion result: {fusion_result}")
        
        # Return the fusion result (which contains ml1, ml2, and final predictions)
        return fusion_result
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API request failed: {str(e)}")
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        print(f"[ERROR] Unexpected error in predict_disease_from_conversation: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

# ---------------- Routes ----------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "SwinSACA Flask API"})

@app.route("/cors-test", methods=["GET", "POST", "OPTIONS"])
def cors_test():
    """Test endpoint to verify CORS is working"""
    if request.method == "OPTIONS":
        # Handle preflight request
        response = jsonify({"message": "CORS preflight successful"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Language, X-Mode")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        return response
    
    return jsonify({
        "message": "CORS test successful",
        "method": request.method,
        "origin": request.headers.get("Origin", "No origin header"),
        "headers": dict(request.headers)
    })

@chat_ns.route("/")
class Chat(Resource):
    @chat_ns.expect(chat_request_model)
    @chat_ns.marshal_with(chat_response_model)
    def post(self):
        """Chat with the SwinSACA medical assistant - handles both text and voice input"""
        if request.content_type and 'multipart/form-data' in request.content_type:
            return self._handle_voice_input()
        else:
            return self._handle_text_input()

    # ------------------------------- #
    # Helpers for summary + HTTP I/O  #
    # ------------------------------- #
    def _build_summary_for_models(self, state_copy: dict, latest_user_text: str, conversation_history: list = None) -> str:
        """Build a comprehensive summary from conversation history, dialog state slots, and latest user text."""
        try:
            # First check if there's an explicit summary in the state
            state_summary = (state_copy or {}).get("summary") or ""
            if isinstance(state_summary, str) and state_summary.strip():
                return state_summary.strip()

            summary_parts = []
            
            # Add complete conversation history if available
            if conversation_history and len(conversation_history) > 0:
                conversation_text = []
                for msg in conversation_history:
                    if isinstance(msg, dict):
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if role and content:
                            conversation_text.append(f"{role}: {content}")
                    elif isinstance(msg, str):
                        conversation_text.append(msg)
                
                if conversation_text:
                    full_conversation = " | ".join(conversation_text)
                    summary_parts.append(f"Complete conversation history: {full_conversation}")

            # Build summary from dialog state slots
            slots = (state_copy or {}).get("slots", {})
            active_domain = (state_copy or {}).get("active_domain")
            stage = (state_copy or {}).get("stage")
            
            if active_domain and slots:
                # Add domain context
                summary_parts.append(f"Patient reporting {active_domain} symptoms.")
                
                # Add slot information based on domain
                if active_domain == "fever":
                    if "duration" in slots:
                        summary_parts.append(f"Fever duration: {slots['duration']}")
                    if "temperature" in slots:
                        summary_parts.append(f"Maximum temperature: {slots['temperature']}")
                    if "assoc" in slots and slots["assoc"]:
                        summary_parts.append(f"Associated symptoms: {', '.join(slots['assoc'])}")
                        
                elif active_domain == "headache":
                    if "duration" in slots:
                        summary_parts.append(f"Headache duration: {slots['duration']}")
                    if "severity" in slots:
                        summary_parts.append(f"Pain severity: {slots['severity']}")
                    if "location" in slots:
                        summary_parts.append(f"Pain location: {slots['location']}")
                    if "assoc" in slots and slots["assoc"]:
                        summary_parts.append(f"Associated symptoms: {', '.join(slots['assoc'])}")
                        
                elif active_domain == "cough":
                    if "type" in slots:
                        summary_parts.append(f"Cough type: {slots['type']}")
                    if "duration" in slots:
                        summary_parts.append(f"Cough duration: {slots['duration']}")
                    if "sputum_color" in slots:
                        summary_parts.append(f"Sputum color: {slots['sputum_color']}")
                    if "red_flags" in slots and slots["red_flags"]:
                        summary_parts.append(f"Respiratory red flags: {', '.join(slots['red_flags'])}")
                        
                elif active_domain == "stomach":
                    if "duration" in slots:
                        summary_parts.append(f"Stomach issue duration: {slots['duration']}")
                    if "severity" in slots:
                        summary_parts.append(f"Pain severity: {slots['severity']}")
                    if "location" in slots:
                        summary_parts.append(f"Pain location: {slots['location']}")
                    if "assoc" in slots and slots["assoc"]:
                        summary_parts.append(f"Associated symptoms: {', '.join(slots['assoc'])}")
                        
                elif active_domain == "fatigue":
                    if "duration" in slots:
                        summary_parts.append(f"Fatigue duration: {slots['duration']}")
                    if "severity" in slots:
                        summary_parts.append(f"Fatigue severity: {slots['severity']}")
                    if "assoc" in slots and slots["assoc"]:
                        summary_parts.append(f"Associated symptoms: {', '.join(slots['assoc'])}")
                        
                elif active_domain == "skin":
                    if "duration" in slots:
                        summary_parts.append(f"Skin issue duration: {slots['duration']}")
                    if "location" in slots:
                        summary_parts.append(f"Affected area: {slots['location']}")
                    if "appearance" in slots:
                        summary_parts.append(f"Skin appearance: {slots['appearance']}")
                    if "assoc" in slots and slots["assoc"]:
                        summary_parts.append(f"Associated symptoms: {', '.join(slots['assoc'])}")

            # Add latest user text if available
            if latest_user_text and latest_user_text.strip():
                summary_parts.append(f"Latest user input: {latest_user_text.strip()}")

            # Combine all parts
            if summary_parts:
                full_summary = " ".join(summary_parts)
                # Limit to reasonable length for ML models (increased to accommodate conversation history)
                return full_summary[:2000]
            else:
                # Fallback to latest user text
                text = (latest_user_text or "").strip()
                if not text:
                    return "No clear user summary available."
                return " ".join(text.split())[:800]
                
        except Exception as e:
            print(f"[ERROR] Error building summary: {str(e)}")
            # Fallback to latest user text
            text = (latest_user_text or "").strip()
            if not text:
                return "No clear user summary available."
            return " ".join(text.split())[:800]

    def _post_json(self, url: str, payload: dict, timeout: int = 10) -> dict:
        """POST JSON with robust error handling; returns {ok, json|error, status, body?}."""
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            ct = resp.headers.get("Content-Type", "")
            if resp.ok:
                try:
                    return {"ok": True, "json": resp.json(), "status": resp.status_code}
                except Exception:
                    return {"ok": True, "json": {"_raw_text": resp.text}, "status": resp.status_code}
            else:
                import json
                body = resp.text if "application/json" not in ct else json.dumps(resp.json(), ensure_ascii=False)
                return {"ok": False, "error": f"HTTP {resp.status_code}", "body": body, "status": resp.status_code}
        except requests.Timeout:
            return {"ok": False, "error": "timeout", "body": None, "status": None}
        except requests.ConnectionError as ce:
            return {"ok": False, "error": f"connection_error: {ce}", "body": None, "status": None}
        except Exception as e:
            return {"ok": False, "error": f"unexpected_error: {e}", "body": None, "status": None}

    def _call_fusion_compare(self, summary_text: str, topk: int = 3) -> dict:
        """
        Fusion/compare expects:
          Input: {"input": "<summary>", "topk": 3}
          Output (example): {
            "input": "...",
            "ml1": {...},     # includes severity, probs, disease_topk, etc.
            "ml2": {...},     # includes predicted_label, probability, top[]
            "final": {...}    # fused decision
          }
        """
        print(f"[DEBUG] Calling fusion/compare API with summary:")
        print(f"   Summary text: {summary_text[:200]}...")
        print(f"   URL: {FUSION_URL}")
        
        payload = {"input": summary_text, "topk": int(topk)}
        result = self._post_json(FUSION_URL, payload)
        
        print(f"[DEBUG] Fusion API response:")
        print(f"   Success: {result.get('ok')}")
        print(f"   Status: {result.get('status')}")
        if not result.get('ok'):
            print(f"   Error: {result.get('error')}")
            print(f"   Body: {result.get('body')}")
        
        return result

    # -------------------- #
    # Voice input handling #
    # -------------------- #
    def _handle_voice_input(self):
        audio_file = None
        lang = "english"
        mode = "voice"

        try:
            print(f"[DEBUG] Voice chat request received:")
            print(f"   Content-Type: {request.content_type}")
            print(f"   Files: {list(request.files.keys())}")
            print(f"   Form data: {dict(request.form)}")
            print(f"   Headers: {dict(request.headers)}")

            if 'audio' not in request.files:
                print("[ERROR] No audio file in request.files")
                api.abort(400, "No audio file provided")

            audio_file = request.files['audio']
            print(f"[DEBUG] Audio file details:")
            print(f"   Filename: '{audio_file.filename}'")
            print(f"   Content type: {audio_file.content_type}")
            print(f"   MIME type: {audio_file.mimetype}")

            audio_content = audio_file.read()
            audio_file.seek(0)
            print(f"   Size: {len(audio_content)} bytes")

            if not audio_file.filename:
                print("[ERROR] Audio file has no filename")
                api.abort(400, "No audio file selected")
            if len(audio_content) == 0:
                print("[ERROR] Audio file is empty")
                api.abort(400, "Audio file is empty")

            lang_raw = (request.headers.get("X-Language") or request.form.get("language") or "english").lower()
            mode = (request.headers.get("X-Mode") or request.form.get("mode") or "voice").lower()

            if lang_raw in ["en", "english"]:
                lang = "english"
            elif lang_raw in ["arr", "arrernte"]:
                lang = "arrernte"
            else:
                lang = lang_raw

            print(f"   Final lang: {lang}")
            print(f"   Final mode: {mode}")

        except Exception as e:
            print(f"[ERROR] Exception in voice chat endpoint: {str(e)}")
            api.abort(500, f"Internal server error: {str(e)}")

        if lang == "english" and mode == "voice":
            try:
                transcribed_text = self._call_transcribe_api(audio_file)
                print(f"[DEBUG] Transcribed text from API: {transcribed_text}")

                normalized_text = normalize_numbers_in_text(transcribed_text)
                print(f"[DEBUG] Normalized text for chatbot: {normalized_text}")

                user_msg_for_bot = normalized_text

                # Route message through your existing chat logic
                bot_reply_english = route_message(user_msg_for_bot)
                state_copy = _copy_state()

                replaced_out = []
                final_reply = bot_reply_english
                if lang == "arrernte":
                    final_reply, replaced_out = _apply_arrernte_glossary_to_reply(bot_reply_english)

                is_final_message = False
                disease_prediction = None
                summary_text = None
                ml1_json = None
                ml2_json = None
                fused_json = None
                fusion_resp = None
                
                if ("summary" in bot_reply_english.lower()
                        or "assessment" in bot_reply_english.lower()
                        or "Thanks for the details" in bot_reply_english):
                    is_final_message = True
                    disease_prediction = predict_disease_from_conversation(user_msg_for_bot, state_copy, None)  # Voice input doesn't have conversation history yet
                    
                    # ---------- Call ML models only for final messages ----------
                    print(f"[DEBUG] Final message detected - calling ML models:")
                    print(f"   Dialog state: {state_copy}")
                    print(f"   Latest user text: {user_msg_for_bot}")
                    
                    summary_text = self._build_summary_for_models(state_copy, user_msg_for_bot)
                    print(f"   Generated summary: {summary_text}")
                    
                    fusion_resp = self._call_fusion_compare(summary_text, topk=3)
                    fused_json = fusion_resp.get("json") if fusion_resp.get("ok") else {
                        "error": fusion_resp.get("error"),
                        "body": fusion_resp.get("body")
                    }

                    # Extract ml1/ml2 blocks if present (for convenience in your UI)
                    ml1_json = (fused_json or {}).get("ml1")
                    ml2_json = (fused_json or {}).get("ml2")
                else:
                    print(f"[DEBUG] Not a final message - skipping ML model calls")

                audio_url = text_to_speech(final_reply, "en")

                return {
                    "reply": final_reply,
                    "transcribed_text": transcribed_text,
                    "normalized_text": normalized_text,
                    "context": {"language": lang, "mode": mode},
                    "replaced_words": replaced_out,
                    "state": state_copy,
                    "bot": bot_name,
                    "is_final_message": is_final_message,
                    "disease_prediction": disease_prediction,
                    "audio_url": audio_url,

                    # --- Model fusion outputs ---
                    "summary_for_models": summary_text,
                    "ml1_result": ml1_json,
                    "ml2_result": ml2_json,
                    "fused_result": fused_json,
                    "model_calls": {
                        "fusion_compare": {
                            "url": FUSION_URL,
                            "ok": fusion_resp.get("ok") if fusion_resp else False,
                            "status": fusion_resp.get("status") if fusion_resp else None
                        }
                    },
                }
            except Exception as e:
                print(f"[ERROR] Error processing voice chat: {str(e)}")
                import traceback
                traceback.print_exc()
                api.abort(500, f"Error processing voice message: {str(e)}")
        else:
            api.abort(400, f"Voice chat only supports English language and voice mode. Received: lang={lang}, mode={mode}")

    def _call_transcribe_api(self, audio_file):
        try:
            print(f"[DEBUG] Calling transcribe API for audio file: {audio_file.filename}")
            with app.test_request_context('/api/chat/transcribe',
                                          method='POST',
                                          data={'audio': audio_file},
                                          content_type='multipart/form-data'):
                transcribe_resource = Transcribe()
                result = transcribe_resource.post()
                if isinstance(result, dict) and 'text' in result:
                    transcribed_text = result['text']
                    print(f"[DEBUG] Transcribe API returned: '{transcribed_text}'")
                    return transcribed_text
                else:
                    print(f"[ERROR] Unexpected transcribe API response: {result}")
                    return "I have a headache and feel dizzy"
        except Exception as e:
            print(f"[ERROR] Failed to call transcribe API: {str(e)}")
            import traceback
            traceback.print_exc()
            return transcribe_audio_file(audio_file)

    # ------------------- #
    # Text input handling #
    # ------------------- #
    def _handle_text_input(self):
        data = request.get_json(silent=True) or {}
        user_msg_raw = (data.get("message") or "").strip()
        if not user_msg_raw:
            api.abort(400, "Provide JSON with 'message'")

        if data.get("reset"):
            reset_state()

        ctx = data.get("_context") or {}
        lang = (request.headers.get("X-Language") or ctx.get("language") or "english").lower()
        mode = (request.headers.get("X-Mode") or ctx.get("mode") or "text").lower()
        conversation_history = data.get("conversation_history", [])

        print(f"[DEBUG] Received session variables:")
        print(f"   X-Language header: {request.headers.get('X-Language')}")
        print(f"   X-Mode header: {request.headers.get('X-Mode')}")
        print(f"   Context language: {ctx.get('language')}")
        print(f"   Context mode: {ctx.get('mode')}")
        print(f"   Final lang: {lang}")
        print(f"   Final mode: {mode}")
        print(f"   User message: {user_msg_raw}")
        print(f"   Conversation history length: {len(conversation_history)}")

        user_msg_for_bot = user_msg_raw
        input_replaced = []
        if lang == "arrernte":
            user_msg_for_bot, input_replaced = translate_arr_to_english_simple(user_msg_raw)

        bot_reply_english = route_message(user_msg_for_bot)
        state_copy = _copy_state()

        replaced_out = []
        final_reply = bot_reply_english
        if lang == "arrernte":
            final_reply, replaced_out = _apply_arrernte_glossary_to_reply(bot_reply_english)

        is_final_message = False
        disease_prediction = None
        summary_text = None
        ml1_json = None
        ml2_json = None
        fused_json = None
        fusion_resp = None
        
        if "Thanks—please tell me a bit more so I can assess this carefully" in bot_reply_english:
            pass
        elif ("summary" in bot_reply_english.lower()
              or "assessment" in bot_reply_english.lower()
              or "Thanks for the details" in bot_reply_english):
            is_final_message = True
            disease_prediction = predict_disease_from_conversation(user_msg_for_bot, state_copy, conversation_history)
            
            # ---------- Call ML models only for final messages ----------
            print(f"[DEBUG] Final message detected - calling ML models (text input):")
            print(f"   Dialog state: {state_copy}")
            print(f"   Latest user text: {user_msg_for_bot}")
            
            summary_text = self._build_summary_for_models(state_copy, user_msg_for_bot)
            print(f"   Generated summary: {summary_text}")
            
            fusion_resp = self._call_fusion_compare(summary_text, topk=3)
            fused_json = fusion_resp.get("json") if fusion_resp.get("ok") else {
                "error": fusion_resp.get("error"),
                "body": fusion_resp.get("body")
            }
            ml1_json = (fused_json or {}).get("ml1")
            ml2_json = (fused_json or {}).get("ml2")
        else:
            print(f"[DEBUG] Not a final message - skipping ML model calls (text input)")

        return {
            "reply": final_reply,
            "transcribed_text": None,
            "normalized_text": None,
            "context": {"language": lang, "mode": mode},
            "replaced_words": replaced_out,
            "state": state_copy,
            "bot": bot_name,
            "is_final_message": is_final_message,
            "disease_prediction": disease_prediction,

            # --- Model fusion outputs ---
            "summary_for_models": summary_text,
            "ml1_result": ml1_json,
            "ml2_result": ml2_json,
            "fused_result": fused_json,
            "model_calls": {
                "fusion_compare": {
                    "url": FUSION_URL,
                    "ok": fusion_resp.get("ok") if fusion_resp else False,
                    "status": fusion_resp.get("status") if fusion_resp else None
                }
            },
            "audio_url": None
        }


# Create a model for transcribe response
transcribe_response_model = api.model('TranscribeResponse', {
    'text': fields.String(description='Transcribed text from audio input')
})

# Create a parser for file upload
transcribe_parser = api.parser()
transcribe_parser.add_argument('audio', 
                              type=FileStorage, 
                              location='files',
                              required=True,
                              help='Audio file to transcribe (WebM, MP4, WAV, etc.)')

@chat_ns.route("/transcribe")
class Transcribe(Resource):
    @chat_ns.doc('transcribe_audio', parser=transcribe_parser)
    @chat_ns.marshal_with(transcribe_response_model)
    def post(self):
        """
        Transcribe audio with Whisper (English)
        
        Send an audio file (WebM, MP4, WAV, etc.) and get back the transcribed text.
        
        **Request Format:**
        - Content-Type: multipart/form-data
        - Field name: 'audio'
        - File: Audio file (any format supported by Whisper)
        
        **Example using curl:**
        ```bash
        curl -X POST http://localhost:5000/api/chat/transcribe \
          -F "audio=@your_audio_file.webm"
        ```
        """
        if "audio" not in request.files:
            api.abort(400, "No 'audio' file provided")
        
        f = request.files["audio"]
        if not f.filename:
            api.abort(400, "Empty filename")
        
        try:
            # Use the shared transcription function
            transcribed_text = transcribe_audio_file(f)
            return {"text": transcribed_text}
        except Exception as e:
            print(f"[ERROR] Transcription endpoint failed: {str(e)}")
            api.abort(500, f"Transcription failed: {str(e)}")

@translate_ns.route("/to_arrernte")
class TranslateToArrernte(Resource):
    @translate_ns.expect(translate_request_model)
    @translate_ns.marshal_with(translate_response_model)
    def post(self):
        """Translate English text to Arrernte using glossary"""
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            api.abort(400, "Provide JSON with 'text'")
        
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
        return {"original_text": text, "translated_text": translated, "replaced_words": replaced}

@translate_ns.route("/to_english")
class TranslateToEnglish(Resource):
    @translate_ns.expect(translate_request_model)
    @translate_ns.marshal_with(translate_response_model)
    def post(self):
        """Translate Arrernte text to English using glossary"""
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            api.abort(400, "Provide JSON with 'text'")
        
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
        return {"original_text": text, "translated_text": translated, "replaced_words": replaced}

# Simple translation function for Arrernte to English
def translate_arr_to_english_simple(text: str):
    """Simple translation function for Arrernte to English"""
    replaced = []
    if not text or not ARR2ENG:
        return text, replaced

    def repl(m):
        w = m.group(0)
        k = w.lower()
        if k in ARR2ENG:
            entry = ARR2ENG[k]
            replaced.append({
                "arrernte": w,
                "english": entry.get("english", w),
                "audio_url": entry.get("audio_url", "")
            })
            return entry.get("english", w)
        return w

    translated = re.sub(r"\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\b", repl, text)
    return translated, replaced

# Add a simple root endpoint
@app.route('/')
def home():
    return {
        'message': 'SwinSACA API is running!',
        'version': '1.0',
        'endpoints': {
            'swagger': '/api/swagger/',
            'health': '/health',
            'cors_test': '/cors-test',
            'auth': '/api/auth/',
            'chat': '/api/chat/ (supports both text and voice)',
            'transcribe': '/api/chat/transcribe (standalone transcription)',
            'translate_arrernte': '/api/translate/to_arrernte',
            'translate_english': '/api/translate/to_english'
        },
        'cors_origins': CORS_ORIGINS
    }

# Serve static audio files
@app.route('/static/audio/<filename>')
def serve_audio(filename):
    """Serve generated TTS audio files"""
    try:
        audio_path = os.path.join(BASE_DIR, "static", "audio", filename)
        if os.path.exists(audio_path):
            return send_file(audio_path, mimetype='audio/wav')
        else:
            return jsonify({"error": "Audio file not found"}), 404
    except Exception as e:
        print(f"[ERROR] Error serving audio file {filename}: {str(e)}")
        return jsonify({"error": "Error serving audio file"}), 500

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
