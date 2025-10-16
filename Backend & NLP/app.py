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

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173').split(',')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app, 
     resources={r"/*": {"origins": CORS_ORIGINS}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Language", "X-Mode"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

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
    print("✅ [SUCCESS] All heavy dependencies loaded successfully!")
    print("   - faster_whisper: ✅")
    print("   - pydub: ✅") 
    print("   - pyttsx3: ✅")
    print("   - rapidfuzz: ✅")
except ImportError as e:
    HEAVY_DEPS_AVAILABLE = False
    print("❌ [ERROR] Some optional dependencies not available. Audio features will be limited.")
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
    print(f"🎤 [INFO] Loading Whisper model: {WHISPER_MODEL}")
    try:
        whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("✅ [SUCCESS] Whisper model loaded successfully!")
        print(f"   Model: {WHISPER_MODEL}")
        print(f"   Device: cpu")
        print(f"   Compute type: int8")
    except Exception as e:
        print(f"❌ [ERROR] Failed to load Whisper model: {str(e)}")
        import traceback
        traceback.print_exc()
        whisper_model = None
else:
    print("⚠️ [WARNING] Heavy dependencies not available, Whisper model not loaded")
    whisper_model = None

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
def predict_disease_from_conversation(final_user_message, dialog_state):
    """
    Predict disease based on conversation history and final user message.
    
    TODO: Replace this function with actual model API call.
    This is where you'll integrate your disease prediction model.
    
    Args:
        final_user_message (str): The final message from the user
        dialog_state (dict): The current dialog state with collected information
    
    Returns:
        dict: Disease prediction results
    """
    # TODO: Replace this with actual model API call
    # Example structure for the API call:
    # 
    # import requests
    # 
    # # Prepare the data for the model
    # model_input = {
    #     "symptoms": final_user_message,
    #     "dialog_state": dialog_state,
    #     "conversation_history": "..."  # You might want to pass the full conversation
    # }
    # 
    # # Call your model API
    # response = requests.post("YOUR_MODEL_API_ENDPOINT", json=model_input)
    # return response.json()
    
    # For now, return a mock prediction
    return {
        "predicted_diseases": [
            {
                "name": "Migraine",
                "confidence": 0.75,
                "description": "Severe headache with possible nausea and light sensitivity"
            },
            {
                "name": "Tension Headache", 
                "confidence": 0.60,
                "description": "Mild to moderate headache often caused by stress"
            }
        ],
        "recommendations": [
            "Rest in a dark, quiet room",
            "Apply cold compress to forehead",
            "Consider over-the-counter pain relief",
            "Consult a doctor if symptoms worsen"
        ],
        "severity": "moderate",
        "urgency": "non-urgent"
    }

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
        # Check if this is a voice input (FormData with audio file)
        if request.content_type and 'multipart/form-data' in request.content_type:
            return self._handle_voice_input()
        else:
            return self._handle_text_input()
    
    def _handle_voice_input(self):
        """Handle voice input - transcribe audio and process"""
        # Initialize variables
        audio_file = None
        lang = "english"
        mode = "voice"
        
        try:
            # Log all request data for debugging
            print(f"[DEBUG] Voice chat request received:")
            print(f"   Content-Type: {request.content_type}")
            print(f"   Files: {list(request.files.keys())}")
            print(f"   Form data: {dict(request.form)}")
            print(f"   Headers: {dict(request.headers)}")
            
            # Check if audio file is present
            if 'audio' not in request.files:
                print("[ERROR] No audio file in request.files")
                api.abort(400, "No audio file provided")
            
            audio_file = request.files['audio']
            print(f"[DEBUG] Audio file details:")
            print(f"   Filename: '{audio_file.filename}'")
            print(f"   Content type: {audio_file.content_type}")
            print(f"   MIME type: {audio_file.mimetype}")
            
            # Read the file content to check size
            audio_content = audio_file.read()
            audio_file.seek(0)  # Reset file pointer
            print(f"   Size: {len(audio_content)} bytes")
            
            if not audio_file.filename or audio_file.filename == '':
                print("[ERROR] Audio file has no filename")
                api.abort(400, "No audio file selected")
            
            if len(audio_content) == 0:
                print("[ERROR] Audio file is empty")
                api.abort(400, "Audio file is empty")
            
            # Get language and mode from headers or form data
            lang_raw = (request.headers.get("X-Language") or request.form.get("language") or "english").lower()
            mode = (request.headers.get("X-Mode") or request.form.get("mode") or "voice").lower()
            
            # Normalize language codes
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
        
        # Check if it's English and voice mode
        if lang == "english" and mode == "voice":
            try:
                # Transcribe audio to text using the transcribe API
                transcribed_text = self._call_transcribe_api(audio_file)
                print(f"[DEBUG] Transcribed text from API: {transcribed_text}")
                
                # Normalize numbers in the transcribed text for better chatbot recognition
                normalized_text = normalize_numbers_in_text(transcribed_text)
                print(f"[DEBUG] Normalized text for chatbot: {normalized_text}")
                
                # Process the normalized text through the chat system
                user_msg_for_bot = normalized_text
                input_replaced = []
                
                # Route message through the chat system
                bot_reply_english = route_message(user_msg_for_bot)
                state_copy = _copy_state()
                
                # Post-process bot reply to Arrernte if client requested Arrernte
                replaced_out = []
                final_reply = bot_reply_english
                if lang == "arrernte":
                    final_reply, replaced_out = _apply_arrernte_glossary_to_reply(bot_reply_english)
                
                # Check if this is a final message for disease prediction
                is_final_message = False
                disease_prediction = None
                
                if "summary" in bot_reply_english.lower() or "assessment" in bot_reply_english.lower() or "Thanks for the details" in bot_reply_english:
                    is_final_message = True
                    disease_prediction = predict_disease_from_conversation(user_msg_for_bot, state_copy)
                
                # Generate audio response
                audio_url = text_to_speech(final_reply, "en")
                
                return {
                    "reply": final_reply,
                    "transcribed_text": transcribed_text,  # Original transcribed text
                    "normalized_text": normalized_text,    # Normalized text sent to chatbot
                    "context": {"language": lang, "mode": mode},
                    "replaced_words": replaced_out,
                    "state": state_copy,
                    "bot": bot_name,
                    "is_final_message": is_final_message,
                    "disease_prediction": disease_prediction,
                    "audio_url": audio_url
                }
            except Exception as e:
                print(f"[ERROR] Error processing voice chat: {str(e)}")
                import traceback
                traceback.print_exc()
                api.abort(500, f"Error processing voice message: {str(e)}")
        else:
            api.abort(400, f"Voice chat only supports English language and voice mode. Received: lang={lang}, mode={mode}")
    
    def _call_transcribe_api(self, audio_file):
        """
        Call the transcribe API internally to get transcribed text.
        
        Args:
            audio_file: The audio file to transcribe
            
        Returns:
            str: Transcribed text
        """
        try:
            print(f"[DEBUG] Calling transcribe API for audio file: {audio_file.filename}")
            
            # Create a mock request context for the transcribe endpoint
            with app.test_request_context('/api/chat/transcribe', 
                                        method='POST',
                                        data={'audio': audio_file},
                                        content_type='multipart/form-data'):
                # Create and call the Transcribe resource
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
            # Fallback to direct transcription
            return transcribe_audio_to_text(audio_file)
    
    def _handle_text_input(self):
        """Handle text input - original chat functionality"""
        data = request.get_json(silent=True) or {}
        user_msg_raw = (data.get("message") or "").strip()
        if not user_msg_raw:
            api.abort(400, "Provide JSON with 'message'")

        # Optional: reset dialog flow
        if data.get("reset"):
            reset_state()

        ctx = data.get("_context") or {}
        lang = (request.headers.get("X-Language") or ctx.get("language") or "english").lower()
        mode = (request.headers.get("X-Mode") or ctx.get("mode") or "text").lower()
        
        # Log received session variables for debugging
        print(f"[DEBUG] Received session variables:")
        print(f"   X-Language header: {request.headers.get('X-Language')}")
        print(f"   X-Mode header: {request.headers.get('X-Mode')}")
        print(f"   Context language: {ctx.get('language')}")
        print(f"   Context mode: {ctx.get('mode')}")
        print(f"   Final lang: {lang}")
        print(f"   Final mode: {mode}")
        print(f"   User message: {user_msg_raw}")

        # ---------- 1) Pre-translate user input if client says it's Arrernte ----------
        user_msg_for_bot = user_msg_raw
        input_replaced = []
        if lang == "arrernte":
            # Simple translation for now - can be enhanced later
            user_msg_for_bot, input_replaced = translate_arr_to_english_simple(user_msg_raw)

        # ---------- 2) Route message (in English if we just translated) ----------
        bot_reply_english = route_message(user_msg_for_bot)
        state_copy = _copy_state()

        # ---------- 3) Post-process bot reply to Arrernte if client requested Arrernte ----------
        replaced_out = []
        final_reply = bot_reply_english
        if lang == "arrernte":
            final_reply, replaced_out = _apply_arrernte_glossary_to_reply(bot_reply_english)

        # ---------- 4) Check if this is a final message for disease prediction ----------
        is_final_message = False
        disease_prediction = None
        
        # Check if the bot is asking for more details (indicating we're in the assessment phase)
        if "Thanks—please tell me a bit more so I can assess this carefully" in bot_reply_english:
            # This is the trigger message - the next user message will be the final one
            # We'll mark this in the response so the frontend knows to expect a final message
            pass
        elif "summary" in bot_reply_english.lower() or "assessment" in bot_reply_english.lower() or "Thanks for the details" in bot_reply_english:
            # This indicates we're at the end of the conversation
            is_final_message = True
            
            # Collect all user messages for disease prediction
            # TODO: Replace this with actual model API call
            # For now, we'll simulate the process
            disease_prediction = predict_disease_from_conversation(user_msg_for_bot, state_copy)

        return {
            "reply": final_reply,
            "transcribed_text": None,  # No transcription for text mode
            "normalized_text": None,   # No normalization for text mode
            "context": {"language": lang, "mode": mode},
            "replaced_words": replaced_out,   # replacements made in BOT reply (EN → Arr)
            "state": state_copy,
            "bot": bot_name,
            "is_final_message": is_final_message,
            "disease_prediction": disease_prediction,
            "audio_url": None  # No audio for text mode
        }

def transcribe_audio_file(audio_file):
    """
    Shared transcription function used by both /transcribe endpoint and /chat endpoint.
    
    Args:
        audio_file: The audio file to transcribe
        
    Returns:
        str: Transcribed text
    """
    try:
        print(f"[DEBUG] Transcription attempt - HEAVY_DEPS_AVAILABLE: {HEAVY_DEPS_AVAILABLE}")
        print(f"[DEBUG] Whisper model status: {whisper_model is not None}")
        print(f"[DEBUG] Audio file details: {audio_file.filename}, {audio_file.content_type}")
        
        if not HEAVY_DEPS_AVAILABLE:
            print("[WARNING] Heavy dependencies not available, using mock transcription")
            return "I have a headache and feel dizzy"
            
        if whisper_model is None:
            print("[WARNING] Whisper model is None, using mock transcription")
            return "I have a headache and feel dizzy"
        
        # Save the audio file to a temporary location
        suffix = os.path.splitext(audio_file.filename)[1] if audio_file.filename else ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Convert to WAV format for better Whisper compatibility
            wav_path = temp_path.replace(suffix, '.wav')
            try:
                if HEAVY_DEPS_AVAILABLE:
                    from pydub import AudioSegment
                    # Load the audio file
                    audio = AudioSegment.from_file(temp_path)
                    # Export as WAV
                    audio.export(wav_path, format="wav")
                    print(f"[DEBUG] Converted audio to WAV: {wav_path}")
                    # Use the WAV file for transcription
                    transcription_path = wav_path
                else:
                    print("[WARNING] pydub not available, using original format")
                    transcription_path = temp_path
            except Exception as e:
                print(f"[WARNING] Audio conversion failed: {str(e)}, using original format")
                transcription_path = temp_path
            
            # Transcribe using Whisper
            print(f"[DEBUG] Transcribing audio file: {transcription_path}")
            print(f"[DEBUG] Audio file size: {os.path.getsize(transcription_path)} bytes")
            
            segments, info = whisper_model.transcribe(transcription_path, language="en")
            print(f"[DEBUG] Whisper info: {info}")
            
            # Combine all segments into a single text
            transcribed_text = ""
            segment_count = 0
            for segment in segments:
                print(f"[DEBUG] Segment {segment_count}: '{segment.text}' (start: {segment.start}, end: {segment.end})")
                transcribed_text += segment.text + " "
                segment_count += 1
            
            transcribed_text = transcribed_text.strip()
            print(f"[DEBUG] Whisper transcription result: '{transcribed_text}'")
            print(f"[DEBUG] Total segments processed: {segment_count}")
            
            # If transcription is empty or too short, use a fallback
            if not transcribed_text or len(transcribed_text.strip()) < 2:
                print("[WARNING] Whisper returned empty or very short transcription")
                return "I have a headache and feel dizzy"
            
            return transcribed_text
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(temp_path)
            except:
                pass
            try:
                if 'wav_path' in locals() and os.path.exists(wav_path):
                    os.unlink(wav_path)
            except:
                pass
                
    except Exception as e:
        print(f"[ERROR] Transcription failed: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fallback to mock transcription
        return "I have a headache and feel dizzy"

def transcribe_audio_to_text(audio_file):
    """
    Wrapper function for backward compatibility.
    """
    return transcribe_audio_file(audio_file)

def normalize_numbers_in_text(text):
    """
    Convert written numbers to digits for better chatbot recognition.
    
    Args:
        text: Input text that may contain written numbers
        
    Returns:
        str: Text with numbers normalized to digits
    """
    if not text:
        return text
    
    # Dictionary mapping written numbers to digits
    number_mapping = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
        'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
        'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
        'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
        'eighty': '80', 'ninety': '90', 'hundred': '100'
    }
    
    # Time-related mappings
    time_mappings = {
        'one day': '1 day', 'two days': '2 days', 'three days': '3 days',
        'four days': '4 days', 'five days': '5 days', 'six days': '6 days',
        'seven days': '7 days', 'one week': '1 week', 'two weeks': '2 weeks',
        'three weeks': '3 weeks', 'one month': '1 month', 'two months': '2 months',
        'three months': '3 months', 'six months': '6 months', 'one year': '1 year',
        'one hour': '1 hour', 'two hours': '2 hours', 'three hours': '3 hours',
        'four hours': '4 hours', 'five hours': '5 hours', 'six hours': '6 hours',
        'one minute': '1 minute', 'two minutes': '2 minutes', 'five minutes': '5 minutes',
        'ten minutes': '10 minutes', 'fifteen minutes': '15 minutes', 'thirty minutes': '30 minutes',
        'one second': '1 second', 'two seconds': '2 seconds', 'five seconds': '5 seconds'
    }
    
    # Convert to lowercase for matching
    text_lower = text.lower()
    
    # First, handle time expressions (more specific)
    for written, digit in time_mappings.items():
        if written in text_lower:
            text = text.replace(written, digit)
            text_lower = text.lower()  # Update lowercase version
    
    # Then handle individual numbers
    for written, digit in number_mapping.items():
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + written + r'\b'
        text = re.sub(pattern, digit, text, flags=re.IGNORECASE)
    
    print(f"[DEBUG] Number normalization: '{text}'")
    return text

def text_to_speech(text, language="en"):
    """
    Convert text to speech audio file using pyttsx3.
    
    Args:
        text: The text to convert to speech
        language: The language code (e.g., 'en' for English)
        
    Returns:
        str: URL to the generated audio file
    """
    try:
        if not HEAVY_DEPS_AVAILABLE:
            print("[WARNING] pyttsx3 not available, using mock audio URL")
            return f"/api/audio/mock_{uuid.uuid4().hex}.mp3"
        
        # Create a unique filename for the audio file
        audio_filename = f"tts_{uuid.uuid4().hex}.wav"
        audio_path = os.path.join(BASE_DIR, "static", "audio", audio_filename)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Generate the audio file
        print(f"[DEBUG] Generating TTS audio for: '{text[:50]}...'")
        tts_to_file(text, audio_path)
        
        # Return the URL path
        audio_url = f"/static/audio/{audio_filename}"
        print(f"[DEBUG] TTS audio generated: {audio_url}")
        
        return audio_url
        
    except Exception as e:
        print(f"[ERROR] TTS generation failed: {str(e)}")
        # Fallback to mock audio URL
        return f"/api/audio/mock_{uuid.uuid4().hex}.mp3"


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
