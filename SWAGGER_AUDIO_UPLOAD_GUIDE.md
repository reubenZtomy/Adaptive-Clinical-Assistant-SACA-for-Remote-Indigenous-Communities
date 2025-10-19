# Swagger UI Audio Upload Guide

This guide explains how to use the Swagger UI interface to upload and analyze audio files with the Arrernte Audio Analysis API.

## 🚀 Getting Started

### 1. Start the Flask API
```bash
python "Backend & NLP/app.py"
```

### 2. Open Swagger UI
Navigate to: `http://localhost:5000/` in your web browser

You should see the Swagger UI interface with all available API endpoints.

## 📁 Available Audio Endpoints

### 1. Test Upload Endpoint
**Path:** `POST /api/arrernte/test_upload`

**Purpose:** Test file upload functionality without processing audio

**Use this first to verify file upload works correctly.**

### 2. Audio Analysis Endpoint  
**Path:** `POST /api/arrernte/analyze_audio`

**Purpose:** Full audio analysis with transcription, translation, and medical symptom detection

**Use this for complete audio analysis.**

## 🎯 Step-by-Step Instructions

### Step 1: Test File Upload

1. **Find the Test Upload endpoint** in Swagger UI
2. **Click "Try it out"** button
3. **Click "Choose File"** and select an audio file (WAV, MP3, M4A, or OGG)
4. **Set force_language** (optional):
   - `auto` - Let Whisper detect language automatically
   - `en` - Force English language detection
5. **Click "Execute"** button
6. **Check the response** - you should see file information like:
   ```json
   {
     "filename": "your_audio.wav",
     "content_type": "audio/wav",
     "content_length": 123456,
     "force_language": "auto",
     "status": "File received successfully",
     "message": "File upload test passed! You can now use the /analyze_audio endpoint."
   }
   ```

### Step 2: Full Audio Analysis

1. **Find the Audio Analysis endpoint** in Swagger UI
2. **Click "Try it out"** button
3. **Click "Choose File"** and select an audio file
4. **Set force_language** (optional):
   - `auto` - Let Whisper detect language automatically
   - `en` - Force English language detection
5. **Click "Execute"** button
6. **Wait for processing** (may take 10-30 seconds depending on audio length)
7. **View the analysis results** including:
   - Transcribed text
   - Translated text
   - Detected medical symptoms
   - Follow-up questions
   - Confidence scores
   - Processing notes

## 📊 Understanding the Response

### Successful Analysis Response
```json
{
  "transcribed_text": "I have a headache and feel nauseous",
  "translated_text": "I have a headache and feel nauseous",
  "detected_symptoms": {
    "headache": {
      "intent": "Symptom_Headache",
      "keywords_found": ["headache"],
      "associated_found": ["nausea"],
      "locations_found": [],
      "confidence": 2
    },
    "stomach": {
      "intent": "Symptom_Stomach", 
      "keywords_found": ["nausea"],
      "associated_found": [],
      "locations_found": [],
      "confidence": 1
    }
  },
  "followup_questions": [
    "Where exactly is the headache—front, back, sides, left or right?",
    "Are you experiencing nausea, light sensitivity, fever, or stiff neck?"
  ],
  "confidence_score": 0.8,
  "replaced_words": [],
  "language_detected": "en",
  "processing_notes": [
    "Audio transcribed successfully. Language detected: en (confidence: 0.95)",
    "Translation completed. 0 words translated from glossary.",
    "Detected 2 symptom categories."
  ]
}
```

## 🔧 Troubleshooting

### Common Issues

1. **"No audio file provided"**
   - Make sure you clicked "Choose File" and selected a file
   - Check that the file is a supported audio format (WAV, MP3, M4A, OGG)

2. **"Audio transcription not available"**
   - The Whisper AI dependencies are not installed
   - Install with: `pip install faster-whisper pydub rapidfuzz`

3. **"Request timeout"**
   - The audio file is too large or processing is taking too long
   - Try with a shorter audio file (under 30 seconds)
   - Check that the Flask app is still running

4. **"No speech detected"**
   - The audio file doesn't contain clear speech
   - Try a different audio file with clear speech
   - Check audio quality and volume

5. **Swagger UI not loading**
   - Make sure Flask app is running on port 5000
   - Check that no other application is using port 5000
   - Try refreshing the browser page

### File Size Limits
- **Recommended:** Under 10MB for best performance
- **Maximum:** 50MB (may cause timeouts)
- **Best format:** WAV files for highest quality

### Processing Time
- **Short audio (5-10 seconds):** 5-15 seconds
- **Medium audio (30-60 seconds):** 15-45 seconds  
- **Long audio (2+ minutes):** 1-3 minutes

## 🎤 Sample Audio Files

You can test with the sample audio files in the project:

### Medical Question Samples
- `Backend & NLP/clips/Headache/` - Headache-related questions
- `Backend & NLP/clips/Fever/` - Fever-related questions
- `Backend & NLP/clips/Cough or Respiratory Flow/` - Breathing questions
- `Backend & NLP/clips/Stomach/` - Stomach-related questions
- `Backend & NLP/clips/Fatigue/` - Fatigue questions
- `Backend & NLP/clips/Skin Rash/` - Skin condition questions

### Quick Test Commands
```bash
# List all available sample files
python test_audio_upload.py --list-samples

# Test with a specific sample file
python test_audio_upload.py "Backend & NLP/clips/Headache/I'm sorry to hear about the pain. Where exactly is the headache—front, back, sides, left or right.mp3"
```

## 💡 Tips for Best Results

1. **Use clear audio** - Avoid background noise
2. **Speak clearly** - Enunciate words properly
3. **Use appropriate language** - English or Arrernte
4. **Keep files short** - Under 60 seconds for faster processing
5. **Test with sample files first** - Verify everything works
6. **Check the test upload endpoint** - Ensure file upload works before full analysis

## 🔍 API Documentation

For complete API documentation, see:
- `ARRERNTEAUDIO_API_DOCUMENTATION.md` - Full API reference
- Swagger UI at `http://localhost:5000/` - Interactive documentation

---

**Happy Testing! 🎤✨**

The Swagger UI provides an easy way to test the audio analysis API without writing any code. Just upload a file and see the results!


