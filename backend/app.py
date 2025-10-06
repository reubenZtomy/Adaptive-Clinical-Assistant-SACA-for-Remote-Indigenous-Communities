#!/usr/bin/env python3
"""
Flask API for Medical Diagnosis using Q-Learning
Educational example – NOT for clinical or medical use.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import pickle
import os
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import KMeans
from datasets import load_dataset
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables for model components
vectorizer = None
label_encoder = None
kmeans = None
Q_table = None
unique_labels = None
actions = None
n_actions = None
n_clusters = None

class MedicalDiagnosisAPI:
    """Medical diagnosis API using Q-learning model"""
    
    def __init__(self):
        self.vectorizer = None
        self.label_encoder = None
        self.kmeans = None
        self.Q_table = None
        self.unique_labels = None
        self.actions = None
        self.n_actions = None
        self.n_clusters = None
        
    def load_model_components(self):
        """Load the trained model components"""
        try:
            # Load vectorizer
            with open("model_components/vectorizer.pkl", "rb") as f:
                self.vectorizer = pickle.load(f)
            
            # Load label encoder
            with open("model_components/label_encoder.pkl", "rb") as f:
                self.label_encoder = pickle.load(f)
            
            # Load kmeans
            with open("model_components/kmeans.pkl", "rb") as f:
                self.kmeans = pickle.load(f)
            
            # Set up actions
            self.unique_labels = self.label_encoder.classes_
            self.ABSTAIN = "Abstain"
            self.actions = list(self.unique_labels) + [self.ABSTAIN]
            self.n_actions = len(self.actions)
            self.n_clusters = self.kmeans.n_clusters
            
            print(f"Loaded model with {self.n_actions} actions and {self.n_clusters} state clusters")
            return True
            
        except Exception as e:
            print(f"Error loading model components: {e}")
            return False
    
    def preprocess_symptoms(self, symptom_text):
        """Preprocess user input symptoms"""
        # Clean and normalize the text
        symptom_text = symptom_text.lower().strip()
        
        # Remove extra whitespace and split by common delimiters
        symptoms = re.split(r'[,;.\n]', symptom_text)
        symptoms = [s.strip() for s in symptoms if s.strip()]
        
        # Join symptoms into a single text for TF-IDF
        processed_text = " ".join(symptoms)
        
        return processed_text
    
    def predict_condition(self, symptom_text):
        """Predict medical condition from symptoms"""
        try:
            # Preprocess symptoms
            processed_text = self.preprocess_symptoms(symptom_text)
            
            # Convert to TF-IDF vector
            symptom_vector = self.vectorizer.transform([processed_text])
            
            # Get state cluster
            state_cluster = self.kmeans.predict(symptom_vector.toarray())[0]
            
            # Get Q-values for this state
            if self.Q_table is not None:
                q_values = self.Q_table[state_cluster]
            else:
                # If no Q-table loaded, return random prediction
                q_values = np.random.random(self.n_actions)
            
            # Get top 5 predictions
            top_indices = np.argsort(q_values)[-5:][::-1]
            
            predictions = []
            for i, idx in enumerate(top_indices):
                action = self.actions[idx]
                confidence = float(q_values[idx])
                predictions.append({
                    "rank": i + 1,
                    "condition": action,
                    "confidence": confidence
                })
            
            # Get the best prediction
            best_idx = int(np.argmax(q_values))
            best_condition = self.actions[best_idx]
            best_confidence = float(q_values[best_idx])
            
            return {
                "best_prediction": {
                    "condition": best_condition,
                    "confidence": best_confidence
                },
                "top_predictions": predictions,
                "state_cluster": int(state_cluster),
                "symptoms_processed": processed_text
            }
            
        except Exception as e:
            return {
                "error": f"Prediction failed: {str(e)}",
                "best_prediction": {"condition": "Unknown", "confidence": 0.0},
                "top_predictions": []
            }

# Initialize the API
api = MedicalDiagnosisAPI()

@app.route('/', methods=['GET'])
def home():
    """Serve the HTML interface"""
    return send_from_directory('static', 'index.html')

@app.route('/api', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        "message": "Medical Diagnosis API using Q-Learning",
        "version": "1.0",
        "endpoints": {
            "/predict": "POST - Predict medical condition from symptoms",
            "/health": "GET - Check API health",
            "/model_info": "GET - Model information"
        },
        "example_usage": {
            "endpoint": "/predict",
            "method": "POST",
            "body": {
                "symptoms": "I am facing headache, shivers, fever"
            }
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    model_loaded = api.vectorizer is not None
    return jsonify({
        "status": "healthy" if model_loaded else "model_not_loaded",
        "model_loaded": model_loaded,
        "n_actions": api.n_actions,
        "n_clusters": api.n_clusters
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Predict medical condition from symptoms"""
    try:
        # Get symptoms from request
        data = request.get_json()
        
        if not data or 'symptoms' not in data:
            return jsonify({
                "error": "Please provide symptoms in the request body",
                "example": {
                    "symptoms": "I am facing headache, shivers, fever"
                }
            }), 400
        
        symptoms = data['symptoms']
        
        if not symptoms or not symptoms.strip():
            return jsonify({
                "error": "Symptoms cannot be empty"
            }), 400
        
        # Make prediction
        result = api.predict_condition(symptoms)
        
        # Add metadata
        result["input_symptoms"] = symptoms
        result["timestamp"] = str(np.datetime64('now'))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Prediction failed: {str(e)}",
            "best_prediction": {"condition": "Unknown", "confidence": 0.0}
        }), 500

@app.route('/predict_batch', methods=['POST'])
def predict_batch():
    """Predict multiple symptom sets at once"""
    try:
        data = request.get_json()
        
        if not data or 'symptoms_list' not in data:
            return jsonify({
                "error": "Please provide symptoms_list in the request body",
                "example": {
                    "symptoms_list": [
                        "I am facing headache, shivers",
                        "cough, fever, fatigue"
                    ]
                }
            }), 400
        
        symptoms_list = data['symptoms_list']
        
        if not isinstance(symptoms_list, list):
            return jsonify({
                "error": "symptoms_list must be a list"
            }), 400
        
        results = []
        for i, symptoms in enumerate(symptoms_list):
            result = api.predict_condition(symptoms)
            result["batch_index"] = i
            result["input_symptoms"] = symptoms
            results.append(result)
        
        return jsonify({
            "batch_results": results,
            "total_predictions": len(results)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Batch prediction failed: {str(e)}"
        }), 500

@app.route('/model_info', methods=['GET'])
def model_info():
    """Get information about the loaded model"""
    if api.vectorizer is None:
        return jsonify({
            "error": "Model not loaded",
            "message": "Please train the model first using Q-learning_improved.py"
        }), 400
    
    return jsonify({
        "model_loaded": True,
        "n_actions": api.n_actions,
        "n_clusters": api.n_clusters,
        "unique_conditions": list(api.unique_labels),
        "actions": api.actions,
        "vectorizer_features": api.vectorizer.max_features,
        "kmeans_clusters": api.kmeans.n_clusters
    })

def initialize_api():
    """Initialize the API and load model components"""
    print("Initializing Medical Diagnosis API...")
    
    # Check if model components exist
    if not os.path.exists("model_components/vectorizer.pkl"):
        print("Model components not found. Please run Q-learning_improved.py first to train the model.")
        return False
    
    # Load model components
    if api.load_model_components():
        print("Model components loaded successfully!")
        
        # Try to load Q-table if available
        q_table_path = "model_components/q_table.npy"
        if os.path.exists(q_table_path):
            api.Q_table = np.load(q_table_path)
            print(f"Loaded Q-table with shape: {api.Q_table.shape}")
        else:
            print("Q-table not found. Using random predictions.")
            api.Q_table = None
        
        return True
    else:
        print("Failed to load model components.")
        return False

if __name__ == '__main__':
    # Initialize the API
    if initialize_api():
        print("\n" + "="*50)
        print("Medical Diagnosis API is ready!")
        print("="*50)
        print("Available endpoints:")
        print("  GET  / - API information")
        print("  GET  /health - Health check")
        print("  POST /predict - Predict condition from symptoms")
        print("  POST /predict_batch - Batch predictions")
        print("  GET  /model_info - Model information")
        print("\nExample usage:")
        print('curl -X POST http://localhost:5000/predict \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"symptoms": "I am facing headache, shivers, fever"}\'')
        print("\nStarting Flask server...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Failed to initialize API. Please check model components.")
