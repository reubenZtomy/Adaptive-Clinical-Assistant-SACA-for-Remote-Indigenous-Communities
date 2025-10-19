# Arrernte Audio Analysis API Documentation

## Overview
The Arrernte Audio Analysis API provides comprehensive analysis of Arrernte audio recordings for medical symptom detection and follow-up question generation. This API combines speech transcription, glossary-based translation, and medical keyword detection to assist healthcare providers in understanding patient symptoms.

## Endpoint
```
POST /api/arrernte/analyze_audio
```

## Features
- **Audio Transcription**: Uses Whisper AI to transcribe Arrernte audio to text
- **Glossary Translation**: Translates Arrernte text to English using the medical glossary
- **Medical Keyword Detection**: Identifies medical symptoms and associated conditions
- **Follow-up Question Generation**: Suggests appropriate follow-up questions based on detected symptoms
- **Confidence Scoring**: Provides confidence levels for transcription and analysis

## Request Format

### Form Data
- `audio_file` (required): Audio file in WAV/MP3 format
- `force_language` (optional): Force language detection ("en", "auto")

### Example Request
```bash
curl -X POST \
  -F "audio_file=@patient_audio.wav" \
  -F "force_language=auto" \
  http://localhost:5000/api/arrernte/analyze_audio
```

## Response Format

```json
{
  "transcribed_text": "Transcribed text from audio",
  "translated_text": "Translated text to English",
  "detected_symptoms": {
    "symptom_type": {
      "intent": "Intent classification",
      "keywords_found": ["list", "of", "found", "keywords"],
      "associated_found": ["associated", "symptoms"],
      "locations_found": ["body", "locations"],
      "types_found": ["symptom", "types"],
      "confidence": 5
    }
  },
  "followup_questions": [
    "Recommended follow-up questions"
  ],
  "confidence_score": 0.8,
  "replaced_words": [
    {
      "src": "original_word",
      "tgt": "translated_word",
      "audio_urls": ["audio_url"],
      "confidence": 0.5
    }
  ],
  "language_detected": "en",
  "processing_notes": [
    "Processing status messages"
  ]
}
```

## Supported Medical Symptoms

### 1. Headache
- **Keywords**: headache, migraine, head pain, pressure in head, akaperte
- **Associated**: nausea, vomit, vomiting, light, sound, aura, vision, blur, fever, stiff neck, neck, photophobia, phonophobia
- **Locations**: front, back, sides, left, right

### 2. Fever
- **Keywords**: fever, temperature, hot, burning
- **Associated**: chills, shiver, shivering, sweat, sweating, body ache, aches, sore throat, cough

### 3. Cough
- **Keywords**: cough, coughing, wheeze, wheezing
- **Associated**: breathless, short of breath, shortness of breath, difficulty breathing, chest pain, wheezing, blue lips, bluish lips
- **Types**: dry, wet, productive, mucus, phlegm

### 4. Stomach Issues
- **Keywords**: stomach, nausea, nauseous, vomit, diarrhea, bloated, bloat, atnerte
- **Associated**: pain, cramps, burning, acid, reflux
- **Locations**: upper, lower, right, left, center

### 5. Fatigue
- **Keywords**: tired, fatigue, exhausted, drained, weak
- **Associated**: sleep, insomnia, depression, anxiety, weight loss, weight gain

### 6. Skin Issues
- **Keywords**: rash, rashes, itch, itchy, itching, hives, urticaria, red spots, spots, bumps, blister, blisters
- **Associated**: swelling, pain, burning, stinging
- **Locations**: face, arms, legs, torso, back, hands, feet

### 7. Chest Pain
- **Keywords**: chest pain, chest ache, inwenge, heart pain
- **Associated**: shortness of breath, breathless, difficulty breathing, nausea, sweating, arm pain

### 8. Breathing Difficulties
- **Keywords**: shortness of breath, breathless, difficulty breathing, trouble breathing
- **Associated**: chest pain, wheezing, cough, fever

## Follow-up Questions

The API automatically generates appropriate follow-up questions based on detected symptoms:

- **Headache**: Location, associated symptoms (nausea, fever, stiff neck)
- **Fever**: Temperature measurement, associated symptoms (chills, sweating)
- **Cough**: Type (dry/wet), associated symptoms (breathing difficulty, chest pain)
- **Stomach**: Location, associated symptoms (nausea, vomiting, diarrhea)
- **Fatigue**: Sleep quality, associated symptoms
- **Skin**: Location, associated symptoms (itch, pain, swelling)

## Error Handling

### Common Error Responses
- `400 Bad Request`: No audio file provided or empty file
- `500 Internal Server Error`: Transcription or analysis failed
- `500 Service Unavailable`: Missing dependencies (Whisper, etc.)

### Error Response Format
```json
{
  "error": "Error description"
}
```

## Dependencies

The API requires the following Python packages:
- `faster-whisper`: For audio transcription
- `pydub`: For audio processing
- `rapidfuzz`: For fuzzy string matching
- `flask-restx`: For API documentation

## Installation

```bash
pip install faster-whisper pydub rapidfuzz flask-restx
```

## Usage Examples

### Python Example
```python
import requests

# Prepare audio file
with open('patient_audio.wav', 'rb') as audio_file:
    files = {'audio_file': audio_file}
    data = {'force_language': 'auto'}
    
    response = requests.post(
        'http://localhost:5000/api/arrernte/analyze_audio',
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"Detected symptoms: {list(result['detected_symptoms'].keys())}")
    print(f"Follow-up questions: {result['followup_questions']}")
```

### JavaScript Example
```javascript
const formData = new FormData();
formData.append('audio_file', audioFile);
formData.append('force_language', 'auto');

fetch('http://localhost:5000/api/arrernte/analyze_audio', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Detected symptoms:', Object.keys(data.detected_symptoms));
    console.log('Follow-up questions:', data.followup_questions);
});
```

## Testing

Use the provided test script to verify the API functionality:

```bash
python test_audio_analysis_api.py
```

## Notes

- The API uses the Arrernte medical glossary for translation
- Confidence scores range from 0.0 to 1.0
- Processing notes provide detailed information about each step
- The API supports both Arrernte and English audio input
- Audio files should be in WAV or MP3 format for best results

