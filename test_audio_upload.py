#!/usr/bin/env python3
"""
Command-line tool to test the Arrernte Audio Analysis API with audio file uploads
"""

import requests
import os
import sys
import argparse
from pathlib import Path

API_BASE_URL = "http://localhost:5000"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/api/arrernte/analyze_audio"

def check_api_status():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def analyze_audio_file(audio_path, force_language="auto"):
    """Upload and analyze an audio file"""
    
    if not os.path.exists(audio_path):
        print(f"ERROR: File '{audio_path}' not found")
        return False
    
    if not check_api_status():
        print("ERROR: API is not running. Please start the Flask app first.")
        print("   Run: python 'Backend & NLP/app.py'")
        return False
    
    print(f"Analyzing audio file: {audio_path}")
    print(f"Force language: {force_language}")
    print("-" * 50)
    
    try:
        with open(audio_path, 'rb') as audio_file:
            files = {'audio_file': audio_file}
            data = {'force_language': force_language}
            
            print("Uploading and processing...")
            response = requests.post(ANALYZE_ENDPOINT, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                display_results(result)
                return True
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                print(f"API Error ({response.status_code}): {error_data.get('error', 'Unknown error')}")
                return False
                
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out. The audio file might be too large or processing is taking too long.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Network Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return False

def display_results(data):
    """Display the analysis results in a formatted way"""
    
    print("SUCCESS: Analysis completed successfully!")
    print()
    
    # Confidence score
    if 'confidence_score' in data:
        confidence_percent = int(data['confidence_score'] * 100)
        print(f"Confidence Score: {confidence_percent}%")
        print()
    
    # Transcribed and translated text
    print("TRANSCRIPTION:")
    print(f"   Original: {data.get('transcribed_text', 'N/A')}")
    print(f"   Translated: {data.get('translated_text', 'N/A')}")
    print()
    
    # Language detected
    if 'language_detected' in data:
        print(f"Language Detected: {data['language_detected']}")
        print()
    
    # Detected symptoms
    symptoms = data.get('detected_symptoms', {})
    if symptoms:
        print("DETECTED SYMPTOMS:")
        for symptom_type, details in symptoms.items():
            print(f"   - {symptom_type.replace('_', ' ').upper()}")
            if details.get('keywords_found'):
                print(f"     Keywords: {', '.join(details['keywords_found'])}")
            if details.get('associated_found'):
                print(f"     Associated: {', '.join(details['associated_found'])}")
            if details.get('locations_found'):
                print(f"     Locations: {', '.join(details['locations_found'])}")
            if details.get('types_found'):
                print(f"     Types: {', '.join(details['types_found'])}")
            print(f"     Confidence: {details.get('confidence', 'N/A')}")
            print()
    else:
        print("DETECTED SYMPTOMS: None")
        print()
    
    # Follow-up questions
    followup = data.get('followup_questions', [])
    if followup:
        print("RECOMMENDED FOLLOW-UP QUESTIONS:")
        for i, question in enumerate(followup, 1):
            print(f"   {i}. {question}")
        print()
    
    # Translation details
    replaced_words = data.get('replaced_words', [])
    if replaced_words:
        print(f"TRANSLATION DETAILS ({len(replaced_words)} words translated):")
        for word in replaced_words:
            print(f"   {word.get('src', 'N/A')} -> {word.get('tgt', 'N/A')} (confidence: {word.get('confidence', 'N/A')})")
        print()
    
    # Processing notes
    notes = data.get('processing_notes', [])
    if notes:
        print("PROCESSING NOTES:")
        for note in notes:
            print(f"   - {note}")
        print()

def main():
    parser = argparse.ArgumentParser(description='Test Arrernte Audio Analysis API')
    parser.add_argument('audio_file', nargs='?', help='Path to the audio file to analyze')
    parser.add_argument('--force-language', choices=['auto', 'en'], default='auto',
                       help='Force language detection (default: auto)')
    parser.add_argument('--list-samples', action='store_true',
                       help='List available sample audio files')
    
    args = parser.parse_args()
    
    if args.list_samples:
        print("Available sample audio files:")
        sample_dirs = [
            "Backend & NLP/clips",
            "Frontend/public/audio"
        ]
        
        found_files = []
        for sample_dir in sample_dirs:
            if os.path.exists(sample_dir):
                for root, dirs, files in os.walk(sample_dir):
                    for file in files:
                        if file.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg')):
                            full_path = os.path.join(root, file)
                            found_files.append(full_path)
        
        if found_files:
            for i, file_path in enumerate(found_files, 1):
                print(f"   {i}. {file_path}")
        else:
            print("   No audio files found in sample directories")
        return
    
    if not args.audio_file:
        print("ERROR: Please provide an audio file path or use --list-samples")
        parser.print_help()
        sys.exit(1)
    
    # Analyze the audio file
    success = analyze_audio_file(args.audio_file, args.force_language)
    
    if success:
        print("SUCCESS: Analysis completed successfully!")
    else:
        print("FAILED: Analysis failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
