from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, decode_token
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from werkzeug.datastructures import FileStorage
from dotenv import load_dotenv
import os
import csv
import re
from Glossary.glossary_translator import Glossary as _Glossary, translate as _gloss_translate
#import arrernte_classifier as arrcls
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

# --- Audio mapping for follow-up questions ---
def load_audio_mapping():
    """Load the mapping of English questions to audio file paths"""
    mapping = {}
    mapping_file = os.path.join(os.path.dirname(__file__), 'followup_questions_audio_mapping.txt')
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '|' in line:
                    question, audio_path = line.split('|', 1)
                    question = question.strip()
                    audio_path = audio_path.strip()
                    mapping[question] = audio_path
        print(f"[DEBUG] Loaded {len(mapping)} audio mappings")
        return mapping
    except FileNotFoundError:
        print(f"[WARNING] Audio mapping file not found: {mapping_file}")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to load audio mapping: {e}")
        return {}

# Load audio mapping at startup
AUDIO_MAPPING = load_audio_mapping()

def find_audio_for_question(question_text):
    """Find the audio file path for a given question text"""
    # Try exact match first
    if question_text in AUDIO_MAPPING:
        return AUDIO_MAPPING[question_text]
    
    # Try partial matches (in case of slight variations)
    for mapped_question, audio_path in AUDIO_MAPPING.items():
        if mapped_question.lower() in question_text.lower() or question_text.lower() in mapped_question.lower():
            return audio_path
    
    return None

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
User, Prediction = models.create_models(db)
models.User = User
models.Prediction = Prediction
models.db = db

# ---------------- Arrernte chatbot proxy config ----------------
ARR_CHAT_URL = None  # not used anymore; same-process integration

# Import routes after setting db
from routes import auth_ns

# Register namespaces
api.add_namespace(auth_ns, path='/auth')

# Create prediction history namespace
prediction_ns = api.namespace('predictions', description='Prediction history operations')

# Define models for prediction endpoints
save_prediction_model = api.model('SavePrediction', {
    'prediction_text': fields.String(required=True, description='The prediction text'),
    'severity': fields.String(required=True, description='Severity level'),
    'language': fields.String(required=True, description='Language used (english/arrernte)'),
    'mode': fields.String(required=True, description='Mode used (text/voice/images)'),
    'ml1_result': fields.Raw(description='ML1 model results'),
    'ml2_result': fields.Raw(description='ML2 model results'),
    'fused_result': fields.Raw(description='Fused model results')
})

@prediction_ns.route('/save')
class SavePrediction(Resource):
    @jwt_required()
    @api.expect(save_prediction_model)
    def post(self):
        """Save a prediction for the current user"""
        try:
            current_user_id = int(get_jwt_identity())
            user = User.query.get(current_user_id)
            
            if not user:
                return {'message': 'User not found'}, 404
            
            data = request.get_json()
            
            # Create new prediction
            prediction = Prediction(
                user_id=current_user_id,
                prediction_text=data['prediction_text'],
                severity=data['severity'],
                language=data['language'],
                mode=data['mode'],
                ml1_result=data.get('ml1_result'),
                ml2_result=data.get('ml2_result'),
                fused_result=data.get('fused_result')
            )
            
            db.session.add(prediction)
            db.session.commit()
            
            print(f"Prediction saved for user {user.username}: {prediction.id}")
            return {'message': 'Prediction saved successfully', 'prediction_id': prediction.id}, 201
            
        except Exception as e:
            print(f"Error saving prediction: {e}")
            db.session.rollback()
            return {'message': f'Error saving prediction: {str(e)}'}, 500

# Register prediction namespace
api.add_namespace(prediction_ns, path='/predictions')

# Test endpoint to manually save a prediction
@api.route('/test-save-prediction')
class TestSavePrediction(Resource):
    def post(self):
        """Test endpoint to manually save a prediction"""
        try:
            # Create a test prediction
            prediction = Prediction(
                user_id=1,  # Use the existing user
                prediction_text="Test prediction from manual endpoint",
                severity="low",
                language="english",
                mode="text",
                ml1_result={"test": "ml1"},
                ml2_result={"test": "ml2"},
                fused_result={"test": "fused"}
            )
            
            db.session.add(prediction)
            db.session.commit()
            
            return {'message': 'Test prediction saved successfully', 'prediction_id': prediction.id}, 201
            
        except Exception as e:
            print(f"Error saving test prediction: {e}")
            db.session.rollback()
            return {'message': f'Error saving test prediction: {str(e)}'}, 500

# Helper function to save prediction for logged-in users
def save_prediction_if_logged_in(disease_prediction, prediction_text, language, mode, request_headers=None):
    """Save prediction to database if user is logged in"""
    print(f"[DEBUG] save_prediction_if_logged_in called with: prediction_text={prediction_text[:50]}..., language={language}, mode={mode}")
    try:
        # Check if user is logged in by looking for JWT token in headers
        if not request_headers:
            print("[DEBUG] No request headers provided")
            return False
            
        auth_header = request_headers.get('Authorization')
        print(f"[DEBUG] Auth header present: {bool(auth_header)}")
        if not auth_header or not auth_header.startswith('Bearer '):
            print("[DEBUG] No valid Authorization header found")
            return False
            
        # Extract token and verify it
        token = auth_header.split(' ')[1]
        
        try:
            decoded_token = decode_token(token)
            user_id = int(decoded_token['sub'])
            
            # Get severity from disease prediction
            severity = "unknown"
            if disease_prediction and isinstance(disease_prediction, dict):
                if 'final' in disease_prediction and 'severity' in disease_prediction['final']:
                    severity = disease_prediction['final']['severity']
                elif 'ml1' in disease_prediction and 'severity' in disease_prediction['ml1']:
                    severity = disease_prediction['ml1']['severity']
            
            # Create prediction record
            prediction = Prediction(
                user_id=user_id,
                prediction_text=prediction_text,
                severity=severity,
                language=language,
                mode=mode,
                ml1_result=disease_prediction.get('ml1') if disease_prediction else None,
                ml2_result=disease_prediction.get('ml2') if disease_prediction else None,
                fused_result=disease_prediction.get('final') if disease_prediction else None
            )
            
            db.session.add(prediction)
            db.session.commit()
            
            print(f"Prediction saved for user {user_id}: {prediction.id}")
            return True
            
        except Exception as e:
            print(f"Error decoding token or saving prediction: {e}")
            return False
            
    except Exception as e:
        print(f"Error in save_prediction_if_logged_in: {e}")
        return False

# --- Chatbot core imports ---
try:
    from Chatbot.chat import route_message, reset_state, predict_tag, bot_name, dialog_state
except ImportError:
    # Fallback if running from different directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Chatbot'))
    from chat import route_message, reset_state, predict_tag, bot_name, dialog_state

# --- Arrernte Chatbot imports (same-process) ---
try:
    from Chatbot_arr.chat import (
        route_message as arr_route_message,
        reset_state as arr_reset_state,
        predict_tag as arr_predict_tag,
        bot_name as arr_bot_name,
        dialog_state as arr_dialog_state,
    )
except ImportError:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Chatbot_arr'))
        from chat import (
            route_message as arr_route_message,
            reset_state as arr_reset_state,
            predict_tag as arr_predict_tag,
            bot_name as arr_bot_name,
            dialog_state as arr_dialog_state,
        )
    except Exception as e:
        arr_route_message = None
        arr_reset_state = None
        arr_predict_tag = None
        arr_bot_name = "ArrBot"
        arr_dialog_state = {}

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
except (ImportError, OSError) as e:
    HEAVY_DEPS_AVAILABLE = False
    print("[ERROR] Some optional dependencies not available. Audio features will be limited.")
    print(f"   Import error: {str(e)}")
    print("   Please install missing dependencies with: pip install faster-whisper pydub pyttsx3 rapidfuzz")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Glossary", "arrernte_audio.csv")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base.en")
CLIPS_DIR = os.path.join(BASE_DIR, "clips")

# Flask-RESTx will automatically generate Swagger documentation

# Create namespaces for API organization
chat_ns = api.namespace('chat', description='Chat and conversation endpoints')
translate_ns = api.namespace('translate', description='Translation endpoints')
ml2_ns = api.namespace('ml2', description='ML Model-2 prediction endpoints')
arrernte_ns = api.namespace('arrernte', description='Arrernte classifier endpoints')
ml1_ns = api.namespace('ml1', description='ML Model-1 triage endpoints')
fusion_ns = api.namespace('fusion', description='Model fusion endpoints')

# Define models for request/response documentation
chat_request_model = api.model('ChatRequest', {
    'message': fields.String(required=True, description='User message to the chatbot', example='I have a headache'),
    'reset': fields.Boolean(description='Reset dialog state', example=False),
    '_context': fields.Raw(description='Context information', example={'language': 'english', 'mode': 'text'})
})

chat_response_model = api.model('ChatResponse', {
    'reply': fields.String(description='Bot response (translated to Arrernte for Arrernte voice mode)'),
    'transcribed_text': fields.String(description='Transcribed text from audio input (English voice mode only)'),
    'normalized_text': fields.String(description='Normalized text sent to chatbot (English voice mode only)'),
    'context': fields.Raw(description='Context information'),
    'replaced_words': fields.List(fields.Raw, description='Words replaced in translation'),
    'state': fields.Raw(description='Dialog state'),
    'bot': fields.String(description='Bot name'),
    'is_final_message': fields.Boolean(description='Whether this is a final message for disease prediction'),
    'disease_prediction': fields.Raw(description='Disease prediction results (if final message)'),
    'audio_url': fields.String(description='URL to the audio response (voice mode only)'),
    'detected_keywords': fields.List(fields.String, description='Detected medical keywords from Arrernte audio (Arrernte voice mode only)'),
    'keyword_string': fields.String(description='Comma-separated string of detected keywords (Arrernte voice mode only)')
})

translate_request_model = api.model('TranslateRequest', {
    'text': fields.String(required=True, description='Text to translate', example='I have a headache')
})

translate_response_model = api.model('TranslateResponse', {
    'original_text': fields.String(description='Original text'),
    'translated_text': fields.String(description='Translated text'),
    'replaced_words': fields.List(fields.Raw, description='Words that were replaced')
})

# Arrernte classifier models
arr_request_model = api.model('ArrernteAnalyzeRequest', {
    'text': fields.String(required=True, description='Input text (Arrernte or English)')
})

arr_classification_model = api.model('ArrernteClassification', {
    'top': fields.String(description='Top category'),
    'scores': fields.Raw(description='Category scores map')
})

arr_keyword_model = api.model('ArrernteKeyword', {
    'input_span': fields.String,
    'canonical': fields.String,
    'category': fields.String,
    'score': fields.Float
})

arr_response_model = api.model('ArrernteAnalyzeResponse', {
    'input': fields.String,
    'keywords_found': fields.List(fields.Nested(arr_keyword_model)),
    'classification': fields.Nested(arr_classification_model),
    'concatenated_string': fields.String
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
ML2_LABEL_NAME_MAP_PATH = os.path.join(ML2_COMPONENTS_DIR, "label_name_map.json")

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
_ml2_label_name_map = None

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

def _ml2_get_label_name_map():
    """Optional mapping of numeric/string label codes -> human disease names.
    File: ML2_LABEL_NAME_MAP_PATH containing {"186": "Migraine", ...}
    """
    global _ml2_label_name_map
    if _ml2_label_name_map is not None:
        return _ml2_label_name_map
    try:
        if os.path.exists(ML2_LABEL_NAME_MAP_PATH):
            import json
            with open(ML2_LABEL_NAME_MAP_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
                _ml2_label_name_map = {str(k): str(v) for k, v in dict(raw).items()}
        else:
            _ml2_label_name_map = {}
    except Exception:
        _ml2_label_name_map = {}
    return _ml2_label_name_map

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
            # Use only the first num_classes Q-values, ignoring the extra action
            num_classes = len(label_encoder.classes_)
            if len(q_values) > num_classes:
                # Use only the first num_classes Q-values (ignore the 21st action)
                q_values_subset = q_values[:num_classes]
                # Apply temperature scaling to make predictions more decisive
                temperature = 0.1
                q_scaled = q_values_subset / temperature
                # Add small random noise to break ties
                noise = np.random.normal(0, 0.001, len(q_scaled))
                q_scaled += noise
                # Apply softmax to get probabilities
                q_shift = q_scaled - float(np.max(q_scaled))
                exp_q = np.exp(q_shift)
                probs = exp_q / float(np.sum(exp_q))
            else:
                # If dimensions match, use original Q-values
                q_shift = q_values - float(np.max(q_values))
                exp_q = np.exp(q_shift)
                probs = exp_q / float(np.sum(exp_q))
            
            best_idx = int(np.argmax(probs))
            top_indices = list(np.argsort(-probs)[:3])
            labels = label_encoder.inverse_transform(np.arange(len(probs)))
        except Exception as e:
            api.abort(500, f"Model inference failed: {str(e)}")

        name_map = _ml2_get_label_name_map()
        def as_name(x):
            sx = str(x)
            return name_map.get(sx, sx)

        return {
            'predicted_label': as_name(labels[best_idx]),
            'probability': float(probs[best_idx]),
            'top': [
                {'label': as_name(labels[i]), 'probability': float(probs[i])}
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
    # Use only the first num_classes Q-values, ignoring the extra action
    num_classes = len(label_encoder.classes_)
    if len(q_values) > num_classes:
        # Use only the first num_classes Q-values (ignore the 21st action)
        q_values_subset = q_values[:num_classes]
        # Apply temperature scaling to make predictions more decisive
        temperature = 0.1
        q_scaled = q_values_subset / temperature
        # Add small random noise to break ties
        noise = np.random.normal(0, 0.001, len(q_scaled))
        q_scaled += noise
        # Apply softmax to get probabilities
        q_shift = q_scaled - float(np.max(q_scaled))
        exp_q = np.exp(q_shift)
        probs = exp_q / float(np.sum(exp_q))
    else:
        # If dimensions match, use original Q-values
        q_shift = q_values - float(np.max(q_values))
        exp_q = np.exp(q_shift)
        probs = exp_q / float(np.sum(exp_q))
    best_idx = int(np.argmax(probs))
    labels = label_encoder.inverse_transform(np.arange(len(probs)))
    top_indices = list(np.argsort(-probs)[:3])
    name_map = _ml2_get_label_name_map()
    def as_name(x):
        sx = str(x)
        return name_map.get(sx, sx)

    return {
        'predicted_label': as_name(labels[best_idx]),
        'probability': float(probs[best_idx]),
        'top': [
            {'label': as_name(labels[i]), 'probability': float(probs[i])}
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
        print("[WARNING] Audio transcription dependencies not available, using fallback")
        return "I have a headache and feel dizzy"  # Fallback text for testing
    
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
            print(f"[DEBUG] Whisper segment: '{segment.text}'")
        
        print(f"[DEBUG] Full transcribed text: '{transcribed_text.strip()}'")
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return transcribed_text.strip()
    except Exception as e:
        print(f"[ERROR] Audio transcription failed: {str(e)}")
        print("[FALLBACK] Using fallback text for testing")
        return "I have a headache and feel dizzy"  # Fallback text for testing

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

# --- Arrernte voice clips lookup ---
def _slugify_filename(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s_-]+", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s

def find_arrernte_clip_for_prompt(prompt_text: str):
    """Given an Arrernte prompt (bot follow-up), try to find a matching audio clip.
    First tries to match against the English question mapping, then falls back to filename matching.
    Returns a URL path like /static/audio/<subdirs>/<file> if found, else None.
    """
    try:
        if not prompt_text:
            return None
            
        # First, try to find audio using our English question mapping
        # We need to check if this is a follow-up question by looking for question patterns
        if '?' in prompt_text or any(word in prompt_text.lower() for word in ['where', 'how', 'what', 'when', 'do you', 'are you', 'have you']):
            # This looks like a follow-up question, try to find matching audio
            audio_path = find_audio_for_question(prompt_text)
            if audio_path:
                # Convert to URL path - remove 'clips/' prefix if present
                if audio_path.startswith('clips/'):
                    audio_path = audio_path[6:]  # Remove 'clips/' prefix
                audio_url = f"http://localhost:5000/static/audio/{audio_path}"
                print(f"[DEBUG] Found audio for follow-up question: {audio_url}")
                return audio_url
        
        # Fallback to original filename matching approach
        if not os.path.isdir(CLIPS_DIR):
            return None
        slug = _slugify_filename(prompt_text)
        best_match = None
        best_len = 0
        for root, _dirs, files in os.walk(CLIPS_DIR):
            for fn in files:
                if not fn.lower().endswith((".mp3", ".wav", ".ogg", ".m4a")):
                    continue
                base = os.path.splitext(fn)[0].lower()
                if base == slug or base.startswith(slug):
                    rel = os.path.relpath(os.path.join(root, fn), CLIPS_DIR).replace("\\", "/")
                    if len(base) > best_len:
                        best_len = len(base)
                        best_match = rel
        if best_match:
            return f"/clips/{best_match}"
        return None
    except Exception:
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
    """Replace words in the bot reply using EN2ARR map (unrestricted glossary-based)."""
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

        if mode == "voice" and lang in ("english", "arrernte"):
            try:
                transcribed_text = self._call_transcribe_api(audio_file)
                print(f"[DEBUG] Transcribed text from API: {transcribed_text}")

                normalized_text = normalize_numbers_in_text(transcribed_text)
                print(f"[DEBUG] Normalized text for chatbot: {normalized_text}")

                # For Arrernte, detect keywords and use them directly for chatbot
                detected_keywords = []
                if lang == "arrernte":
                    # First translate to get English text for keyword detection
                    user_msg_for_bot, _repl = translate_arr_to_english_simple(normalized_text)
                    print(f"[DEBUG] ARR->EN (for keyword detection): {user_msg_for_bot}")
                    
                    # Detect medical keywords in the translated text
                    detected_keywords = detect_medical_keywords_in_text(user_msg_for_bot)
                    if detected_keywords:
                        print(f"[DEBUG] Detected keywords (after Arrernte translation lookup): {detected_keywords}")
                        # Use only the detected keywords as the message for the chatbot
                        keyword_string = ", ".join(detected_keywords)
                        user_msg_for_bot = f"I have {keyword_string}"
                        print(f"[DEBUG] Final chatbot input with Arrernte translations: {user_msg_for_bot}")
                        print(f"[DEBUG] Will route to English chatbot (route_message)")
                    else:
                        # If no keywords detected, use the translated text
                        user_msg_for_bot = user_msg_for_bot
                        print(f"[DEBUG] No keywords detected, using translated text: {user_msg_for_bot}")
                else:
                    user_msg_for_bot = normalized_text

                # Route message through English chat logic
                bot_reply_english = route_message(user_msg_for_bot)
                state_copy = _copy_state()

                replaced_out = []
                final_reply = bot_reply_english
                # For Arrernte voice, convert English reply to Arrernte via glossary
                if lang == "arrernte":
                    final_reply, replaced_out = _apply_arrernte_glossary_to_reply(bot_reply_english)

                is_final_message = False
                disease_prediction = None
                summary_text = None
                ml1_json = None
                ml2_json = None
                fused_json = None
                fusion_resp = None
                
                
                # Check for final message indicators - be more specific to avoid false positives
                final_message_indicators = [
                    "Thanks for the details",  # Specific phrase
                    "arrule",  # Arrernte thanks
                    "arnterre"  # Arrernte medical terms that might indicate summary
                ]
                
                # Only check for exact phrase matches, not partial word matches
                is_final_detected = any(indicator.lower() in bot_reply_english.lower() for indicator in final_message_indicators)
                
                # Also check if the reply contains medical assessment keywords - be more specific
                medical_assessment_keywords = [
                    "diagnosis", "recommendation", "doctor", "hospital",
                    "urgent", "emergency", "treatment", "medication", "follow-up"
                ]
                
                # Only trigger if these keywords appear in a summary context, not in questions
                has_medical_assessment = any(keyword in bot_reply_english.lower() for keyword in medical_assessment_keywords) and not bot_reply_english.strip().endswith('?')
                
                # Only check dialog state if we have a meaningful summary
                # Don't trigger based on dialog state alone for follow-up questions
                has_sufficient_info = False
                
                # Only trigger final message if we have a definitive final summary from the chatbot
                # Look for the word "Summary" (with capital S) which indicates the final summary message
                has_meaningful_summary = (
                    # Look for "Summary" with capital S (most specific indicator)
                    ("Summary" in bot_reply_english) or
                    # Look for "summary:" with colon (backup for lowercase)
                    ("summary:" in bot_reply_english.lower()) or
                    # Look for Arrernte final patterns with "Summary"
                    ("arrule" in bot_reply_english.lower() and "Summary" in bot_reply_english) or
                    ("arrule" in bot_reply_english.lower() and "summary" in bot_reply_english.lower())
                )
                
                if has_meaningful_summary:
                    print(f"[DEBUG] Meaningful summary detected - triggering final message")
                    has_sufficient_info = True
                
                # Trigger final message if any of these conditions are met
                if is_final_detected or has_medical_assessment or has_sufficient_info:
                    is_final_message = True
                    print(f"[DEBUG] Final message triggered - reasons:")
                    print(f"   - Final detected: {is_final_detected}")
                    print(f"   - Medical assessment: {has_medical_assessment}")
                    print(f"   - Sufficient info: {has_sufficient_info}")
                    print(f"   - Meaningful summary: {has_meaningful_summary}")
                    # Use the summary text from the bot reply for prediction, not the initial keywords
                    summary_text_for_prediction = bot_reply_english
                    print(f"[DEBUG] Using summary text for prediction: {summary_text_for_prediction}")
                    disease_prediction = predict_disease_from_conversation(summary_text_for_prediction, state_copy, None)  # Voice input doesn't have conversation history yet
                    
                    # ---------- Call ML models only for final messages ----------
                    print(f"[DEBUG] Final message detected - calling ML models:")
                    print(f"   Dialog state: {state_copy}")
                    print(f"   Summary text for prediction: {summary_text_for_prediction}")
                    
                    summary_text = self._build_summary_for_models(state_copy, summary_text_for_prediction)
                    print(f"   Generated summary: {summary_text}")
                    
                    fusion_resp = self._call_fusion_compare(summary_text, topk=3)
                    fused_json = fusion_resp.get("json") if fusion_resp.get("ok") else {
                        "error": fusion_resp.get("error"),
                        "body": fusion_resp.get("body")
                    }

                    # Extract ml1/ml2 blocks if present (for convenience in your UI)
                    ml1_json = (fused_json or {}).get("ml1")
                    ml2_json = (fused_json or {}).get("ml2")
                    
                    # Save prediction for logged-in users
                    save_prediction_if_logged_in(
                        disease_prediction, 
                        summary_text_for_prediction, 
                        lang, 
                        mode, 
                        request.headers
                    )
                else:
                    print(f"[DEBUG] Not a final message - skipping ML model calls")

                print(f"[CHAT] Voice path lang={lang} mode={mode} -> preparing audio reply")
                audio_url = None
                if lang == "arrernte":
                    # Try to serve pre-recorded Arrernte clip for follow-up prompts
                    # Use the English reply for matching, not the Arrernte translation
                    print(f"[DEBUG] Looking for audio for English reply: {bot_reply_english}")
                    audio_url = find_arrernte_clip_for_prompt(bot_reply_english)
                    if audio_url:
                        print(f"[DEBUG] Found pre-recorded audio: {audio_url}")
                    else:
                        print(f"[DEBUG] No pre-recorded audio found, using TTS fallback")
                        # Fallback to TTS if no clip
                        audio_url = text_to_speech(final_reply, "en")
                else:
                    audio_url = text_to_speech(final_reply, "en")

                # Prepare response based on language
                if lang == "arrernte":
                    # For Arrernte, don't expose transcribed text to frontend
                    return {
                        "reply": final_reply,  # This is already translated to Arrernte
                        "context": {"language": lang, "mode": mode},
                        "replaced_words": replaced_out,
                        "state": state_copy,
                        "bot": bot_name,
                        "is_final_message": is_final_message,
                        "disease_prediction": disease_prediction,
                        "audio_url": audio_url,
                        
                        # --- Keyword detection for Arrernte audio ---
                        "detected_keywords": detected_keywords,
                        "keyword_string": ", ".join(detected_keywords) if detected_keywords else "",

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
                else:
                    # For English, include transcribed text as before
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
            api.abort(400, f"Voice chat only supports language 'english' or 'arrernte' and mode 'voice'. Received: lang={lang}, mode={mode}")

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
        ctx = data.get("_context") or {}
        lang = (request.headers.get("X-Language") or ctx.get("language") or "english").lower()
        mode = (request.headers.get("X-Mode") or ctx.get("mode") or "text").lower()
        user_msg_raw = (data.get("message") or "").strip()
        # Allow empty message for images mode (payload uses selections/final)
        if not user_msg_raw and mode != "images":
            api.abort(400, "Provide JSON with 'message'")

        if data.get("reset"):
            reset_state()
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

        # -------- Images mode (English) integration: build summary and call MLs --------
        if mode == "images" and lang in ["en", "english"]:
            print("[CHAT] Images mode detected (English) - building summary and calling ML models")
            selections = data.get("selections") or []
            notes = (data.get("message") or "").strip()
            is_final = bool(data.get("final"))

            state_copy = _copy_state()
            parts_txt = ", ".join(selections) if selections else "unspecified locations"
            summary_en = f"Patient reports discomfort at: {parts_txt}."
            if notes:
                summary_en += f" Additional notes: {notes}"

            if not is_final:
                return {
                    "reply": "Noted your selections. You can add more areas or confirm when done.",
                    "transcribed_text": None,
                    "normalized_text": None,
                    "context": {"language": "english", "mode": mode},
                    "replaced_words": [],
                    "state": state_copy,
                    "bot": bot_name,
                    "is_final_message": False,
                    "disease_prediction": None,
                    "summary_for_models": summary_en,
                    "ml1_result": None,
                    "ml2_result": None,
                    "fused_result": None,
                    "model_calls": {},
                    "audio_url": None
                }

            # Final: run ML pipeline via existing function
            fusion_result = predict_disease_from_conversation(summary_en, state_copy)
            ml1_json = fusion_result.get("ml1") if isinstance(fusion_result, dict) else None
            ml2_json = fusion_result.get("ml2") if isinstance(fusion_result, dict) else None
            fused_json = fusion_result.get("final") if isinstance(fusion_result, dict) else None

            return {
                "reply": "Thanks. I’ve generated an assessment from your selections.",
                "transcribed_text": None,
                "normalized_text": None,
                "context": {"language": "english", "mode": mode},
                "replaced_words": [],
                "state": state_copy,
                "bot": bot_name,
                "is_final_message": True,
                "disease_prediction": fusion_result,
                "summary_for_models": fusion_result.get("input") if isinstance(fusion_result, dict) else summary_en,
                "ml1_result": ml1_json,
                "ml2_result": ml2_json,
                "fused_result": fused_json,
                "model_calls": {},
                "audio_url": None
            }

        # Route Arrernte text directly to Arrernte chatbot (same process)
        if lang == "arrernte" and mode == "text" and arr_route_message:
            print("[CHAT] Routing to Arrernte chatbot (same process)")
            if data.get("reset") and arr_reset_state:
                arr_reset_state()
            arr_reply = arr_route_message(user_msg_raw)
            state_copy = {
                "active_domain": arr_dialog_state.get("active_domain"),
                "stage": arr_dialog_state.get("stage"),
                "slots": dict(arr_dialog_state.get("slots", {})),
            }
            # Detect final summary message from Arrernte bot
            is_final_message = False
            disease_prediction = None
            summary_for_models_en = None
            ml1_json = None
            ml2_json = None
            fused_json = None

            print(f"[DEBUG] Checking final message conditions for voice input (Arrernte):")
            print(f"   Arrernte reply: '{arr_reply}'")
            print(f"   Contains 'summary': {'summary' in arr_reply.lower()}")
            
            if isinstance(arr_reply, str) and ("summary" in arr_reply.lower()):
                is_final_message = True
                print(f"[DEBUG] Final message detected for voice input (Arrernte)!")
                # Translate latest user input to English for the model summary
                latest_en, _ = translate_arr_to_english_simple(user_msg_raw)
                # Use Arr dialog_state to build the English summary inside predictor
                disease_prediction = predict_disease_from_conversation(latest_en, state_copy)
                if disease_prediction and not disease_prediction.get("error"):
                    summary_for_models_en = disease_prediction.get("input")
                    ml1_json = disease_prediction.get("ml1")
                    ml2_json = disease_prediction.get("ml2")
                    fused_json = disease_prediction.get("final")

            return {
                "reply": arr_reply,
                "transcribed_text": None,
                "normalized_text": None,
                "context": {"language": lang, "mode": mode},
                "replaced_words": [],
                "state": state_copy,
                "bot": arr_bot_name,
                "is_final_message": is_final_message,
                "disease_prediction": disease_prediction,
                "summary_for_models": summary_for_models_en,
                "ml1_result": ml1_json,
                "ml2_result": ml2_json,
                "fused_result": fused_json,
                "model_calls": {},
                "audio_url": None
            }

        print("[CHAT] Routing to main (English) chatbot")
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
        
        print(f"[DEBUG] Checking final message conditions for text input:")
        print(f"   Bot reply: '{bot_reply_english}'")
        print(f"   Contains 'Summary': {'Summary' in bot_reply_english}")
        print(f"   Contains 'summary:': {'summary:' in bot_reply_english.lower()}")
        print(f"   Contains 'summary nhenhe': {'summary nhenhe' in bot_reply_english.lower()}")
        
        if "Thanks—please tell me a bit more so I can assess this carefully" in bot_reply_english:
            print(f"[DEBUG] Skipping - asking for more info")
            pass
        elif (("Summary" in bot_reply_english)
              or ("summary:" in bot_reply_english.lower())
              or ("summary nhenhe" in bot_reply_english.lower())):
            is_final_message = True
            print(f"[DEBUG] Final message detected for text input!")
            # Use the summary text from the bot reply for prediction, not the initial user message
            summary_text_for_prediction = bot_reply_english
            print(f"[DEBUG] Using summary text for prediction (text input): {summary_text_for_prediction}")
            disease_prediction = predict_disease_from_conversation(summary_text_for_prediction, state_copy, conversation_history)
            
            # ---------- Call ML models only for final messages ----------
            print(f"[DEBUG] Final message detected - calling ML models (text input):")
            print(f"   Dialog state: {state_copy}")
            print(f"   Summary text for prediction: {summary_text_for_prediction}")
            
            summary_text = self._build_summary_for_models(state_copy, summary_text_for_prediction)
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

        # Save prediction for logged-in users (text input)
        if is_final_message and disease_prediction:
            save_prediction_if_logged_in(
                disease_prediction, 
                summary_text_for_prediction, 
                lang, 
                mode, 
                request.headers
            )

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
            print(f"[DEBUG] Transcribe endpoint returning: '{transcribed_text}'")
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
        
        try:
            g = _Glossary.load_csv(os.path.join(os.path.dirname(__file__), 'Glossary', 'arrernte_audio.csv'))
            # Whitelist of safe medical terms/directions/units to translate EN -> ARR
            EN_WHITELIST = {
                'headache','fever','cough','stomach','rash','fatigue','pain','temperature','chills','sweating',
                'nausea','vomiting','diarrhea','vision','light','sound','stiff neck','chest','chest pain',
                'shortness','breath','shortness of breath','breathless','week','weeks','day','days','hour','hours',
                'front','back','sides','left','right'
            }
            raw_out, decisions = _gloss_translate(g, text, direction='en2arr')
            # Rebuild output applying only whitelisted replacements
            out_tokens = []
            filtered = []
            for d in decisions:
                src = (d.get('src_span') or '').strip()
                tgt = (d.get('tgt') or '').strip()
                if src.lower() in EN_WHITELIST and tgt:
                    out_tokens.extend(tgt.split(' '))
                    filtered.append({"src": src, "tgt": tgt, "audio_urls": d.get("audio_urls", [])})
                else:
                    out_tokens.extend(src.split(' '))
            # simple detokenize: remove space before punctuation
            out_text = ' '.join(out_tokens)
            out_text = re.sub(r"\s+([.,;:!?])", r"\\1", out_text)
            return {"original_text": text, "translated_text": out_text, "replaced_words": filtered}
        except Exception as e:
            print(f"[ERROR] EN->ARR translation failed: {e}")
            return {"original_text": text, "translated_text": text, "replaced_words": []}

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
        
        try:
            g = _Glossary.load_csv(os.path.join(os.path.dirname(__file__), 'Glossary', 'arrernte_audio.csv'))
            raw_out, decisions = _gloss_translate(g, text, direction='arr2en')
            out_tokens = []
            filtered = []
            for d in decisions:
                src = (d.get('src_span') or '').strip()
                tgt = (d.get('tgt') or '').strip()
                if tgt:
                    out_tokens.extend(tgt.split(' '))
                    filtered.append({"src": src, "tgt": tgt, "audio_urls": d.get("audio_urls", [])})
                else:
                    out_tokens.extend(src.split(' '))
            out_text = ' '.join(out_tokens)
            out_text = re.sub(r"\s+([.,;:!?])", r"\\1", out_text)
            return {"original_text": text, "translated_text": out_text, "replaced_words": filtered}
        except Exception as e:
            print(f"[ERROR] ARR->EN translation failed: {e}")
            return {"original_text": text, "translated_text": text, "replaced_words": []}

@arrernte_ns.route('/analyze')
class ArrernteAnalyze(Resource):
    @arrernte_ns.expect(arr_request_model)
    @arrernte_ns.marshal_with(arr_response_model)
    def post(self):
        """Analyze Arrernte/English text and extract canonical medical keywords and category"""
        data = request.get_json(silent=True) or {}
        raw = (data.get('text') or '').strip()
        if not raw:
            api.abort(400, "Provide JSON with 'text'")
        try:
            chunks = arrcls.split_chunks(raw)
            found = []
            cat_scores = {c: 0.0 for c in arrcls.CATEGORIES}

            for ch in chunks:
                key, ratio, canon, cat = arrcls.fuzzy_match_phrase(ch)
                if canon:
                    found.append({"input_span": ch, "canonical": canon, "category": cat, "score": round(ratio, 3)})
                    cat_scores[cat] += ratio
                else:
                    matches = arrcls.word_level(ch)
                    for token, score, canon_w, cat_w in matches:
                        cat2 = cat_w or "General"
                        found.append({"input_span": token, "canonical": canon_w, "category": cat2, "score": round(score, 3)})
                        cat_scores[cat2] += score

            found = arrcls.dedupe_preserve(found, key=lambda d: d["canonical"])  # type: ignore
            top_cat = max(cat_scores.items(), key=lambda kv: (kv[1], arrcls.CATEGORIES.index(kv[0])))[0] if any(cat_scores.values()) else None
            canon_list = [d["canonical"] for d in found]
            if not canon_list:
                concatenated = ""
            elif len(canon_list) == 1:
                concatenated = canon_list[0]
            else:
                concatenated = ", ".join(canon_list[:-1]) + f", and {canon_list[-1]}"

            return {
                "input": raw,
                "keywords_found": found,
                "classification": {
                    "top": top_cat,
                    "scores": {k: round(v, 3) for k, v in cat_scores.items()}
                },
                "concatenated_string": concatenated
            }
        except Exception as e:
            print(f"[ERROR] Arrernte analyze failed: {e}")
            api.abort(500, f"Analyze failed: {e}")

# Simple translation function for Arrernte to English
def translate_arr_to_english_simple(text: str):
    try:
        g = _Glossary.load_csv(os.path.join(os.path.dirname(__file__), 'Glossary', 'arrernte_audio.csv'))
        raw_out, decisions = _gloss_translate(g, text, direction='arr2en')
        out_tokens = []
        filtered = []
        for d in decisions:
            src = (d.get('src_span') or '').strip()
            tgt = (d.get('tgt') or '').strip()
            if tgt:
                out_tokens.extend(tgt.split(' '))
                filtered.append({"src": src, "tgt": tgt, "audio_urls": d.get("audio_urls", [])})
            else:
                out_tokens.extend(src.split(' '))
        out_text = ' '.join(out_tokens)
        out_text = re.sub(r"\s+([.,;:!?])", r"\\1", out_text)
        
        # Preserve numbers and other non-Arrernte words that might have been lost
        # Split the original text and check if any numbers or English words are missing
        original_words = text.split()
        translated_words = out_text.split()
        
        # Check for missing numbers and common English words
        for word in original_words:
            # If it's a number or common English word, make sure it's preserved
            if (word.isdigit() or 
                word.lower() in ['days', 'day', 'hours', 'hour', 'minutes', 'minute', 'weeks', 'week', 'months', 'month', 'years', 'year', 'ago', 'since', 'for', 'during', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'] or
                word in ['2', '3', '4', '5', '6', '7', '8', '9', '10']):
                if word not in translated_words:
                    # Insert the missing word back into the translated text
                    out_text = out_text + ' ' + word
                    print(f"[DEBUG] Preserved missing word: '{word}'")
        
        return out_text, filtered
    except Exception as e:
        print(f"[ERROR] translate_arr_to_english_simple failed: {e}")
        return text, []

# Medical keywords for detection in translated Arrernte text
# Organized by priority - more specific symptoms first
MEDICAL_KEYWORDS_FOR_CHAT = {
    # Specific symptoms (highest priority)
    "headache": ["headache", "head pain", "migraine", "pressure in head", "akaperte"],
    "chest_pain": ["chest pain", "chest ache", "inwenge", "heart pain"],
    "breathing": ["shortness of breath", "difficulty breathing", "trouble breathing"],
    "fever": ["fever", "temperature", "hot", "burning"],
    "cough": ["cough", "coughing", "wheeze", "wheezing"],
    "skin": ["rash", "rashes", "itch", "itchy", "itching", "hives", "red spots", "spots", "bumps"],
    "fatigue": ["tired", "fatigue", "exhausted", "drained", "weak"],
    "dizziness": ["dizzy", "dizziness", "lightheaded", "vertigo"],
    "vomiting": ["vomit", "vomiting", "throw up"],
    "diarrhea": ["diarrhea", "loose stool", "runny", "watery"],
    "constipation": ["constipation", "constipated", "hard stool", "can't go"],
    "bleeding": ["bleeding", "blood", "bleed", "hemorrhage"],
    "swelling": ["swelling", "swollen", "puffy", "inflamed"],
    "infection": ["infection", "infected", "pus", "discharge"],
    "allergy": ["allergy", "allergic", "reaction", "sensitive"],
    "medication": ["medicine", "medication", "drug", "pill", "tablet"],
    
    # General symptoms (lower priority)
    "stomach": ["stomach", "nausea", "nauseous", "bloated", "bloat", "atnerte"],
    "nausea": ["nauseous", "sick", "queasy"],
    "pain": ["pain", "ache", "hurt", "sore", "uncomfortable"],
    
    # Location descriptors (high priority for medical context)
    "location": ["lower", "upper", "right", "left", "front", "back", "side", "sides", "top", "bottom", "middle", "center", "inner", "outer"],
    
    # Time descriptors (high priority for medical context)
    "time": ["days", "day", "hours", "hour", "minutes", "minute", "weeks", "week", "months", "month", "years", "year", "ago", "since", "for", "during"],
    
    # Severity descriptors (high priority for medical context)
    "severity": ["mild", "moderate", "severe", "intense", "sharp", "dull", "throbbing", "stabbing", "burning", "aching", "cramping"],
    
    # Frequency descriptors (high priority for medical context)
    "frequency": ["always", "often", "sometimes", "rarely", "never", "constantly", "intermittent", "occasional", "frequent", "daily", "weekly"],
    
    # Numbers (detect any numeric values - both digits and words)
    "numbers": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "100", "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred"],
    
    # Emergency (highest priority when present)
    "emergency": ["emergency", "urgent", "critical", "help"]
}

def detect_medical_keywords_in_text(text: str) -> list:
    """
    Detect medical keywords in translated text and return a list of specific words found.
    Also checks for Arrernte translations in the glossary and adds them to the keywords.
    
    Args:
        text: The translated English text to scan for keywords
        
    Returns:
        List of specific keywords found in the text (including Arrernte translations)
    """
    if not text:
        return []
    
    text_lower = text.lower()
    detected_keywords = []
    
    # First, detect and combine number + time word combinations
    # This needs to be done before individual keyword detection to avoid duplicates
    number_time_combinations = []
    
    # Find number + time word patterns
    import re
    # Pattern to match number (digit or word) + time word
    number_time_pattern = r'\b(?:(\d+)|(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred))\s+(days?|hours?|minutes?|weeks?|months?|years?)\b'
    
    matches = re.finditer(number_time_pattern, text_lower)
    for match in matches:
        number_part = match.group(1) or match.group(2)  # Either digit or word
        time_part = match.group(3)  # days, hours, etc.
        combined = f"{number_part} {time_part}"
        number_time_combinations.append(combined)
        print(f"[DEBUG] Found number+time combination: '{combined}'")
    
    # Add the combined keywords
    detected_keywords.extend(number_time_combinations)
    
    # Check emergency keywords first (highest priority)
    for keyword in MEDICAL_KEYWORDS_FOR_CHAT.get("emergency", []):
        if keyword.lower() in text_lower:
            detected_keywords.append(keyword)
            break
    
    # Check specific symptoms (high priority)
    specific_categories = ["headache", "chest_pain", "breathing", "fever", "cough", "skin", 
                          "fatigue", "dizziness", "vomiting", "diarrhea", "constipation", 
                          "bleeding", "swelling", "infection", "allergy", "medication"]
    
    for category in specific_categories:
        if category in MEDICAL_KEYWORDS_FOR_CHAT:
            for keyword in MEDICAL_KEYWORDS_FOR_CHAT[category]:
                if keyword.lower() in text_lower:
                    detected_keywords.append(keyword)
                    break
    
    # Check medical context descriptors (high priority) - add all matching keywords
    # But skip individual numbers and time words if they're already in combinations
    context_categories = ["location", "time", "severity", "frequency", "numbers"]
    
    for category in context_categories:
        if category in MEDICAL_KEYWORDS_FOR_CHAT:
            for keyword in MEDICAL_KEYWORDS_FOR_CHAT[category]:
                if keyword.lower() in text_lower:
                    # Skip individual numbers and time words if they're part of a combination
                    skip_keyword = False
                    if category in ["numbers", "time"]:
                        for combination in number_time_combinations:
                            if keyword.lower() in combination:
                                skip_keyword = True
                                print(f"[DEBUG] Skipping '{keyword}' as it's part of combination '{combination}'")
                                break
                    
                    if not skip_keyword:
                        detected_keywords.append(keyword)
    
    # Check general symptoms only if no specific symptoms found
    if not any(cat in detected_keywords for cat in [kw for cat in specific_categories for kw in MEDICAL_KEYWORDS_FOR_CHAT.get(cat, [])]):
        general_categories = ["stomach", "nausea", "pain"]
        for category in general_categories:
            if category in MEDICAL_KEYWORDS_FOR_CHAT:
                for keyword in MEDICAL_KEYWORDS_FOR_CHAT[category]:
                    if keyword.lower() in text_lower:
                        detected_keywords.append(keyword)
                        break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in detected_keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    
    # Check for Arrernte translations in the glossary
    print(f"[DEBUG] Checking for Arrernte translations for keywords: {unique_keywords}")
    try:
        # Fix the path to the glossary file
        glossary_path = os.path.join(os.path.dirname(__file__), 'Glossary', 'arrernte_audio.csv')
        print(f"[DEBUG] Loading glossary from: {glossary_path}")
        
        # Check if file exists
        if not os.path.exists(glossary_path):
            print(f"[ERROR] Glossary file not found at: {glossary_path}")
            return unique_keywords
        
        g = _Glossary.load_csv(glossary_path)
        print(f"[DEBUG] Successfully loaded glossary with {len(g.rows)} entries")
        arrernte_translations = []
        
        for keyword in unique_keywords:
            print(f"[DEBUG] Looking for Arrernte translation for keyword: '{keyword}'")
            # Look for Arrernte translations of the keyword
            for row in g.rows:
                english_meaning = row.get('english_meaning', '')
                arrernte_word = row.get('arrernte_word', '')
                if english_meaning and keyword.lower() in english_meaning.lower():
                    if arrernte_word:
                        arrernte_translations.append(arrernte_word)
                        print(f"[DEBUG] Found Arrernte translation for '{keyword}': '{arrernte_word}' (from '{english_meaning}')")
        
        print(f"[DEBUG] Found {len(arrernte_translations)} Arrernte translations: {arrernte_translations}")
        
        # Track which Arrernte translations belong to location, symptom, and duration keywords
        location_keywords = ["lower", "upper", "right", "left", "front", "back", "side", "sides", "top", "bottom", "middle", "center", "inner", "outer"]
        symptom_keywords = ["nausea", "diarrhea", "stool", "bloating", "appetite", "loss", "vomiting", "constipation", "bleeding", "swelling", "infection", "allergy", "medication"]
        duration_keywords = ["hours", "hour", "days", "day", "minutes", "minute", "weeks", "week", "months", "month", "years", "year", "ago", "since", "for", "during"]
        
        # Also include numbers when they appear with duration keywords (both digits and words)
        number_keywords = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "100", "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred"]
        
        location_arrernte_translations = []
        symptom_arrernte_translations = []
        duration_arrernte_translations = []
        
        # Check if any priority keywords are present
        has_location_keywords = any(keyword.lower() in location_keywords for keyword in unique_keywords)
        has_symptom_keywords = any(keyword.lower() in symptom_keywords for keyword in unique_keywords)
        has_duration_keywords = any(keyword.lower() in duration_keywords for keyword in unique_keywords)
        has_number_keywords = any(keyword.lower() in number_keywords for keyword in unique_keywords)
        
        # If duration keywords are present, also consider numbers as priority
        if has_duration_keywords and has_number_keywords:
            print(f"[DEBUG] Duration keywords with numbers detected - treating numbers as priority")
        
        has_priority_keywords = has_location_keywords or has_symptom_keywords or has_duration_keywords
        
        if has_priority_keywords:
            if has_location_keywords:
                print(f"[DEBUG] Location keywords detected")
            if has_symptom_keywords:
                print(f"[DEBUG] Symptom keywords detected")
            if has_duration_keywords:
                print(f"[DEBUG] Duration keywords detected")
            print(f"[DEBUG] Filtering to keep only priority keywords and their translations")
            
            # Find Arrernte translations specifically for location keywords
            for keyword in unique_keywords:
                if keyword.lower() in location_keywords:
                    # Look for Arrernte translations of this specific location keyword
                    for row in g.rows:
                        english_meaning = row.get('english_meaning', '')
                        arrernte_word = row.get('arrernte_word', '')
                        if english_meaning and keyword.lower() in english_meaning.lower():
                            if arrernte_word:
                                location_arrernte_translations.append(arrernte_word)
                                print(f"[DEBUG] Found location Arrernte translation for '{keyword}': '{arrernte_word}'")
            
            # Find Arrernte translations specifically for symptom keywords
            for keyword in unique_keywords:
                if keyword.lower() in symptom_keywords:
                    # Look for Arrernte translations of this specific symptom keyword
                    for row in g.rows:
                        english_meaning = row.get('english_meaning', '')
                        arrernte_word = row.get('arrernte_word', '')
                        if english_meaning and keyword.lower() in english_meaning.lower():
                            if arrernte_word:
                                symptom_arrernte_translations.append(arrernte_word)
                                print(f"[DEBUG] Found symptom Arrernte translation for '{keyword}': '{arrernte_word}'")
            
            # Find Arrernte translations specifically for duration keywords
            for keyword in unique_keywords:
                if keyword.lower() in duration_keywords:
                    # Look for Arrernte translations of this specific duration keyword
                    for row in g.rows:
                        english_meaning = row.get('english_meaning', '')
                        arrernte_word = row.get('arrernte_word', '')
                        if english_meaning and keyword.lower() in english_meaning.lower():
                            if arrernte_word:
                                duration_arrernte_translations.append(arrernte_word)
                                print(f"[DEBUG] Found duration Arrernte translation for '{keyword}': '{arrernte_word}'")
            
            # Filter to keep only priority keywords and their specific Arrernte translations
            filtered_keywords = []
            priority_keywords = location_keywords + symptom_keywords + duration_keywords
            
            # If duration keywords are present, also include numbers as priority
            if has_duration_keywords and has_number_keywords:
                priority_keywords.extend(number_keywords)
                print(f"[DEBUG] Including numbers as priority keywords due to duration context")
            
            # Keep priority keywords (location, symptom, and duration)
            for keyword in unique_keywords:
                if keyword.lower() in priority_keywords:
                    filtered_keywords.append(keyword)
                    if keyword.lower() in location_keywords:
                        print(f"[DEBUG] Keeping location keyword: '{keyword}'")
                    elif keyword.lower() in symptom_keywords:
                        print(f"[DEBUG] Keeping symptom keyword: '{keyword}'")
                    elif keyword.lower() in duration_keywords:
                        print(f"[DEBUG] Keeping duration keyword: '{keyword}'")
                    elif keyword.lower() in number_keywords and has_duration_keywords:
                        print(f"[DEBUG] Keeping number keyword (duration context): '{keyword}'")
            
            # Keep only Arrernte translations of priority keywords
            for keyword in unique_keywords:
                if keyword not in priority_keywords and keyword in location_arrernte_translations:
                    filtered_keywords.append(keyword)
                    print(f"[DEBUG] Keeping location Arrernte translation: '{keyword}'")
                elif keyword not in priority_keywords and keyword in symptom_arrernte_translations:
                    filtered_keywords.append(keyword)
                    print(f"[DEBUG] Keeping symptom Arrernte translation: '{keyword}'")
                elif keyword not in priority_keywords and keyword in duration_arrernte_translations:
                    filtered_keywords.append(keyword)
                    print(f"[DEBUG] Keeping duration Arrernte translation: '{keyword}'")
                elif keyword not in priority_keywords and keyword not in location_arrernte_translations and keyword not in symptom_arrernte_translations and keyword not in duration_arrernte_translations:
                    print(f"[DEBUG] Removing non-priority keyword: '{keyword}'")
            
            # Also add any Arrernte translations that were found for priority keywords
            for arrernte_word in location_arrernte_translations:
                if arrernte_word not in filtered_keywords:
                    filtered_keywords.append(arrernte_word)
                    print(f"[DEBUG] Adding location Arrernte translation: '{arrernte_word}'")
            
            for arrernte_word in symptom_arrernte_translations:
                if arrernte_word not in filtered_keywords:
                    filtered_keywords.append(arrernte_word)
                    print(f"[DEBUG] Adding symptom Arrernte translation: '{arrernte_word}'")
            
            for arrernte_word in duration_arrernte_translations:
                if arrernte_word not in filtered_keywords:
                    filtered_keywords.append(arrernte_word)
                    print(f"[DEBUG] Adding duration Arrernte translation: '{arrernte_word}'")
            
            unique_keywords = filtered_keywords
            print(f"[DEBUG] Filtered keywords (priority + Arrernte translations): {unique_keywords}")
        else:
            print(f"[DEBUG] No priority keywords (location/symptom/duration) detected, keeping all keywords")
            # Add all Arrernte translations
            unique_keywords.extend(arrernte_translations)
            print(f"[DEBUG] Keywords with all Arrernte translations: {unique_keywords}")
        
    except Exception as e:
        print(f"[ERROR] Failed to load glossary for Arrernte translations: {e}")
    
    return unique_keywords

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

# Serve static audio files (including subdirectories)
@app.route('/static/audio/<path:filepath>')
def serve_audio(filepath):
    """Serve audio files from static/audio directory, including subdirectories"""
    try:
        audio_path = os.path.join(BASE_DIR, "static", "audio", filepath)
        if os.path.exists(audio_path):
            # Determine MIME type based on file extension
            if filepath.lower().endswith('.mp3'):
                mimetype = 'audio/mpeg'
            elif filepath.lower().endswith('.wav'):
                mimetype = 'audio/wav'
            elif filepath.lower().endswith('.ogg'):
                mimetype = 'audio/ogg'
            elif filepath.lower().endswith('.m4a'):
                mimetype = 'audio/mp4'
            else:
                mimetype = 'audio/mpeg'  # Default to MP3
            
            print(f"[DEBUG] Serving audio file: {audio_path} (MIME: {mimetype})")
            return send_file(audio_path, mimetype=mimetype)
        else:
            print(f"[ERROR] Audio file not found: {audio_path}")
            return jsonify({"error": "Audio file not found"}), 404
    except Exception as e:
        print(f"[ERROR] Error serving audio file {filepath}: {str(e)}")
        return jsonify({"error": "Error serving audio file"}), 500

# Serve Arrernte clips (static files under clips/)
@app.route('/clips/<path:subpath>')
def serve_clips(subpath):
    try:
        abs_path = os.path.join(CLIPS_DIR, subpath)
        if os.path.isfile(abs_path):
            return send_file(abs_path)
        return jsonify({"error": "Clip not found"}), 404
    except Exception as e:
        print(f"[ERROR] Error serving clip {subpath}: {str(e)}")
        return jsonify({"error": "Error serving clip"}), 500

# ==================== NEW API: Arrernte Audio Analysis ====================

# Medical keywords and follow-up logic extracted from chat.py
MEDICAL_KEYWORDS = {
    "headache": {
        "keywords": ["headache", "migraine", "head pain", "pressure in head", "akaperte"],
        "associated": ["nausea", "vomit", "vomiting", "light", "sound", "aura", "vision", "blur", "fever", "stiff neck", "neck", "photophobia", "phonophobia"],
        "locations": ["front", "back", "sides", "left", "right"],
        "intent": "Symptom_Headache"
    },
    "fever": {
        "keywords": ["fever", "temperature", "hot", "burning"],
        "associated": ["chills", "shiver", "shivering", "sweat", "sweating", "body ache", "aches", "sore throat", "cough"],
        "intent": "Symptom_Fever"
    },
    "cough": {
        "keywords": ["cough", "coughing", "wheeze", "wheezing"],
        "associated": ["breathless", "short of breath", "shortness of breath", "difficulty breathing", "chest pain", "wheezing", "blue lips", "bluish lips"],
        "types": ["dry", "wet", "productive", "mucus", "phlegm"],
        "intent": "Symptom_Cough"
    },
    "stomach": {
        "keywords": ["stomach", "nausea", "nauseous", "vomit", "diarrhea", "bloated", "bloat", "atnerte"],
        "associated": ["pain", "cramps", "burning", "acid", "reflux"],
        "locations": ["upper", "lower", "right", "left", "center"],
        "intent": "Symptom_Stomach"
    },
    "fatigue": {
        "keywords": ["tired", "fatigue", "exhausted", "drained", "weak"],
        "associated": ["sleep", "insomnia", "depression", "anxiety", "weight loss", "weight gain"],
        "intent": "Symptom_Fatigue"
    },
    "skin": {
        "keywords": ["rash", "rashes", "itch", "itchy", "itching", "hives", "urticaria", "red spots", "spots", "bumps", "blister", "blisters"],
        "associated": ["swelling", "pain", "burning", "stinging"],
        "locations": ["face", "arms", "legs", "torso", "back", "hands", "feet"],
        "intent": "Symptom_SkinRash"
    },
    "chest_pain": {
        "keywords": ["chest pain", "chest ache", "inwenge", "heart pain"],
        "associated": ["shortness of breath", "breathless", "difficulty breathing", "nausea", "sweating", "arm pain"],
        "intent": "ChestPain"
    },
    "breathing": {
        "keywords": ["shortness of breath", "breathless", "difficulty breathing", "trouble breathing"],
        "associated": ["chest pain", "wheezing", "cough", "fever"],
        "intent": "BreathingDifficulty"
    }
}

def detect_medical_keywords(text: str) -> dict:
    """Detect medical keywords in the translated text and return analysis."""
    text_lower = text.lower()
    detected_symptoms = {}
    
    for symptom_type, data in MEDICAL_KEYWORDS.items():
        # Check main keywords
        keyword_matches = []
        for keyword in data["keywords"]:
            if keyword in text_lower:
                keyword_matches.append(keyword)
        
        # Check associated symptoms
        associated_matches = []
        if "associated" in data:
            for assoc in data["associated"]:
                if assoc in text_lower:
                    associated_matches.append(assoc)
        
        # Check locations if applicable
        location_matches = []
        if "locations" in data:
            for location in data["locations"]:
                if location in text_lower:
                    location_matches.append(location)
        
        # Check types if applicable
        type_matches = []
        if "types" in data:
            for type_word in data["types"]:
                if type_word in text_lower:
                    type_matches.append(type_word)
        
        if keyword_matches or associated_matches:
            detected_symptoms[symptom_type] = {
                "intent": data["intent"],
                "keywords_found": keyword_matches,
                "associated_found": associated_matches,
                "locations_found": location_matches,
                "types_found": type_matches,
                "confidence": len(keyword_matches) + len(associated_matches)
            }
    
    return detected_symptoms

def generate_followup_questions(detected_symptoms: dict) -> list:
    """Generate appropriate follow-up questions based on detected symptoms."""
    followup_questions = []
    
    for symptom_type, data in detected_symptoms.items():
        if symptom_type == "headache":
            if not data["locations_found"]:
                followup_questions.append("Where exactly is the headache—front, back, sides, left or right?")
            if not any(assoc in ["nausea", "vomit", "fever", "stiff neck"] for assoc in data["associated_found"]):
                followup_questions.append("Are you experiencing nausea, light sensitivity, fever, or stiff neck?")
        
        elif symptom_type == "fever":
            if not any("temperature" in keyword for keyword in data["keywords_found"]):
                followup_questions.append("What's your temperature?")
            if not data["associated_found"]:
                followup_questions.append("Are you experiencing chills, sweating, body aches, or cough?")
        
        elif symptom_type == "cough":
            if not data["types_found"]:
                followup_questions.append("Is your cough dry or producing mucus/phlegm?")
            if not any(assoc in ["shortness of breath", "chest pain"] for assoc in data["associated_found"]):
                followup_questions.append("Do you have shortness of breath or chest pain?")
        
        elif symptom_type == "stomach":
            if not data["locations_found"]:
                followup_questions.append("Where exactly is the pain—upper, lower, right, left, or center?")
            if not any(assoc in ["nausea", "vomit", "diarrhea"] for assoc in data["associated_found"]):
                followup_questions.append("Are you experiencing nausea, vomiting, or diarrhea?")
        
        elif symptom_type == "fatigue":
            if not any(assoc in ["sleep", "insomnia"] for assoc in data["associated_found"]):
                followup_questions.append("Have you been sleeping well recently?")
        
        elif symptom_type == "skin":
            if not data["locations_found"]:
                followup_questions.append("Where is the rash located on your body?")
            if not any(assoc in ["itch", "pain", "swelling"] for assoc in data["associated_found"]):
                followup_questions.append("Is the rash itchy, painful, or swollen?")
    
    return followup_questions

# Create file upload parser for Swagger UI
audio_upload_parser = api.parser()
audio_upload_parser.add_argument('audio_file', type=FileStorage, location='files', required=True, help='Audio file in WAV/MP3 format')
audio_upload_parser.add_argument('force_language', type=str, location='form', default='auto', help='Force language detection (auto or en)')

# API Models for the new endpoint
arrernte_audio_analysis_response_model = api.model('ArrernteAudioAnalysisResponse', {
    'transcribed_text': fields.String(description='Transcribed text from audio'),
    'translated_text': fields.String(description='Translated text to English'),
    'detected_symptoms': fields.Raw(description='Detected medical symptoms and keywords'),
    'followup_questions': fields.List(fields.String, description='Recommended follow-up questions'),
    'confidence_score': fields.Float(description='Overall confidence in the analysis'),
    'replaced_words': fields.List(fields.Raw, description='Words replaced during translation'),
    'language_detected': fields.String(description='Detected language of the audio'),
    'processing_notes': fields.List(fields.String, description='Processing notes and warnings')
})

@arrernte_ns.route('/analyze_audio')
class ArrernteAudioAnalysis(Resource):
    @arrernte_ns.expect(audio_upload_parser)
    @arrernte_ns.marshal_with(arrernte_audio_analysis_response_model)
    def post(self):
        """Analyze Arrernte audio for medical symptoms and provide follow-up questions
        
        Upload an audio file to:
        1. Transcribe speech to text using Whisper AI
        2. Translate Arrernte to English using medical glossary
        3. Detect medical symptoms and keywords
        4. Generate appropriate follow-up questions
        5. Provide confidence scoring and analysis details
        
        Supported audio formats: WAV, MP3, M4A, OGG
        
        Example usage in Swagger UI:
        1. Click "Try it out" button
        2. Click "Choose File" and select an audio file
        3. Optionally set force_language to "en" or "auto"
        4. Click "Execute" to analyze the audio
        """
        try:
            # Parse arguments from Swagger UI
            args = audio_upload_parser.parse_args()
            audio_file = args['audio_file']
            force_language = args['force_language'] or 'auto'
            
            if not audio_file or not audio_file.filename:
                api.abort(400, "No audio file provided")
            
            processing_notes = []
            
            # Step 1: Transcribe audio
            if not HEAVY_DEPS_AVAILABLE or whisper_model is None:
                print("[WARNING] Audio transcription dependencies not available, using fallback")
                transcribed_text = "I have a headache and feel dizzy"  # Fallback text for testing
                lang = "en"
                lang_prob = 0.8
                processing_notes.append("Audio transcription not available - using fallback text for testing")
            else:
                try:
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                        audio_file.save(tmp_file.name)
                        tmp_path = tmp_file.name
                    
                    # Transcribe using Whisper
                    if force_language == "en":
                        segments, info = whisper_model.transcribe(tmp_path, language="en")
                        lang = "en"
                        lang_prob = 1.0
                    else:
                        segments, info = whisper_model.transcribe(tmp_path)
                        lang = getattr(info, "language", "auto")
                        lang_prob = getattr(info, "language_probability", 0.0)
                    
                    transcribed_text = " ".join(s.text.strip() for s in segments).strip()
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    processing_notes.append(f"Audio transcribed successfully. Language detected: {lang} (confidence: {lang_prob:.2f})")
                    
                except Exception as e:
                    api.abort(500, f"Audio transcription failed: {str(e)}")
            
            if not transcribed_text:
                api.abort(400, "No speech detected in audio file")
            
            # Step 2: Translate using glossary
            try:
                g = _Glossary.load_csv(os.path.join(os.path.dirname(__file__), 'Glossary', 'arrernte_audio.csv'))
                raw_out, decisions = _gloss_translate(g, transcribed_text, direction='arr2en')
                
                # Process translation results
                out_tokens = []
                replaced_words = []
                for d in decisions:
                    src = (d.get('src_span') or '').strip()
                    tgt = (d.get('tgt') or '').strip()
                    if tgt and d.get('score', -999) > -999:  # Only successful translations
                        out_tokens.extend(tgt.split(' '))
                        replaced_words.append({
                            "src": src, 
                            "tgt": tgt, 
                            "audio_urls": d.get("audio_urls", []),
                            "confidence": d.get('score', 0)
                        })
                    else:
                        out_tokens.extend(src.split(' '))
                
                translated_text = ' '.join(out_tokens)
                translated_text = re.sub(r"\s+([.,;:!?])", r"\\1", translated_text)
                
                processing_notes.append(f"Translation completed. {len(replaced_words)} words translated from glossary.")
                
            except Exception as e:
                processing_notes.append(f"Translation failed: {str(e)}. Using original text.")
                translated_text = transcribed_text
                replaced_words = []
            
            # Step 3: Detect medical keywords
            detected_symptoms = detect_medical_keywords(translated_text)
            
            # Step 4: Generate follow-up questions
            followup_questions = generate_followup_questions(detected_symptoms)
            
            # Step 5: Calculate confidence score
            confidence_score = 0.0
            if lang_prob > 0.8:
                confidence_score += 0.3
            if len(replaced_words) > 0:
                confidence_score += 0.3
            if detected_symptoms:
                confidence_score += 0.4
            
            # Add processing notes
            if not detected_symptoms:
                processing_notes.append("No medical symptoms detected in the text.")
            else:
                processing_notes.append(f"Detected {len(detected_symptoms)} symptom categories.")
            
            return {
                "transcribed_text": transcribed_text,
                "translated_text": translated_text,
                "detected_symptoms": detected_symptoms,
                "followup_questions": followup_questions,
                "confidence_score": min(confidence_score, 1.0),
                "replaced_words": replaced_words,
                "language_detected": lang,
                "processing_notes": processing_notes
            }
            
        except Exception as e:
            print(f"[ERROR] Arrernte audio analysis failed: {e}")
            api.abort(500, f"Analysis failed: {str(e)}")

# Simple test endpoint for Swagger UI file upload testing
@arrernte_ns.route('/test_upload')
class TestUpload(Resource):
    @arrernte_ns.expect(audio_upload_parser)
    def post(self):
        """Test endpoint to verify file upload functionality in Swagger UI
        
        This is a simple test endpoint that just returns file information
        without processing the audio. Use this to verify file upload works
        before testing the full analysis endpoint.
        """
        try:
            args = audio_upload_parser.parse_args()
            audio_file = args['audio_file']
            force_language = args['force_language'] or 'auto'
            
            if not audio_file or not audio_file.filename:
                api.abort(400, "No audio file provided")
            
            # Get file information
            file_info = {
                "filename": audio_file.filename,
                "content_type": audio_file.content_type,
                "content_length": audio_file.content_length,
                "force_language": force_language,
                "status": "File received successfully",
                "message": "File upload test passed! You can now use the /analyze_audio endpoint."
            }
            
            return file_info
            
        except Exception as e:
            print(f"[ERROR] Test upload failed: {e}")
            api.abort(500, f"Test upload failed: {str(e)}")

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
