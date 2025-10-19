# Arrernte Audio Upload & Analysis Tools

This directory contains tools to test the new Arrernte Audio Analysis API that can transcribe, translate, and analyze medical symptoms from audio files.

## 🚀 Quick Start

### Option 1: Web Interface (Recommended)
1. **Start the Flask API:**
   ```bash
   python "Backend & NLP/app.py"
   ```

2. **Open the web interface:**
   - Double-click `audio_upload_test.html` to open in your browser
   - Or run: `start_audio_test.bat` (Windows) or `start_audio_test.ps1` (PowerShell)

3. **Upload and analyze:**
   - Drag and drop an audio file or click to select
   - Choose language detection (auto or English)
   - Click "Analyze Audio" to get results

### Option 2: Command Line
1. **Start the Flask API:**
   ```bash
   python "Backend & NLP/app.py"
   ```

2. **List available sample files:**
   ```bash
   python test_audio_upload.py --list-samples
   ```

3. **Analyze an audio file:**
   ```bash
   python test_audio_upload.py "path/to/your/audio.wav"
   python test_audio_upload.py "path/to/your/audio.wav" --force-language en
   ```

## 📁 Files Overview

### Core Files
- **`audio_upload_test.html`** - Web interface for uploading and analyzing audio files
- **`test_audio_upload.py`** - Command-line tool for testing the API
- **`start_audio_test.bat`** - Windows batch file to start everything
- **`start_audio_test.ps1`** - PowerShell script to start everything

### API Files
- **`Backend & NLP/app.py`** - Main Flask API with the new `/api/arrernte/analyze_audio` endpoint
- **`ARRERNTEAUDIO_API_DOCUMENTATION.md`** - Complete API documentation

## 🎯 Features

### Audio Analysis Pipeline
1. **Audio Transcription** - Uses Whisper AI to convert speech to text
2. **Glossary Translation** - Translates Arrernte to English using medical glossary
3. **Medical Keyword Detection** - Identifies 8 major symptom categories:
   - Headache (with location and associated symptoms)
   - Fever (with temperature and associated symptoms)
   - Cough (with type and breathing issues)
   - Stomach (with location and digestive symptoms)
   - Fatigue (with sleep and mental health)
   - Skin (with location and appearance)
   - Chest Pain (with cardiac symptoms)
   - Breathing (with respiratory difficulties)

4. **Follow-up Questions** - Generates relevant medical follow-up questions
5. **Confidence Scoring** - Provides confidence levels for analysis quality

### Supported Audio Formats
- WAV, MP3, M4A, OGG
- Any format supported by Whisper AI

## 📊 Sample Audio Files

The system includes 59 sample audio files in various categories:

### Medical Question Categories
- **Cough/Respiratory** (8 files) - Questions about breathing, cough type, duration
- **Fatigue** (9 files) - Questions about tiredness, sleep, energy levels
- **Fever** (7 files) - Questions about temperature, duration, associated symptoms
- **Headache** (9 files) - Questions about pain location, severity, associated symptoms
- **Skin Rash** (14 files) - Questions about rash appearance, location, triggers
- **Stomach** (8 files) - Questions about pain location, digestive symptoms

### Welcome Audio
- **Frontend Audio** (4 files) - Welcome messages and instructions

## 🔧 API Usage Examples

### cURL Example
```bash
curl -X POST \
  -F "audio_file=@patient_audio.wav" \
  -F "force_language=auto" \
  http://localhost:5000/api/arrernte/analyze_audio
```

### Python Example
```python
import requests

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

## 📋 Response Format

```json
{
  "transcribed_text": "Transcribed text from audio",
  "translated_text": "Translated text to English",
  "detected_symptoms": {
    "headache": {
      "intent": "Symptom_Headache",
      "keywords_found": ["headache"],
      "associated_found": ["nausea"],
      "locations_found": ["front"],
      "confidence": 2
    }
  },
  "followup_questions": [
    "Where exactly is the headache—front, back, sides, left or right?"
  ],
  "confidence_score": 0.8,
  "replaced_words": [
    {
      "src": "ayenge",
      "tgt": "I",
      "audio_urls": [],
      "confidence": 0.4
    }
  ],
  "language_detected": "en",
  "processing_notes": [
    "Audio transcribed successfully",
    "Translation completed. 1 words translated from glossary."
  ]
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **"API is not running"**
   - Make sure Flask app is started: `python "Backend & NLP/app.py"`
   - Check that port 5000 is available

2. **"Audio transcription not available"**
   - Install required dependencies: `pip install faster-whisper pydub rapidfuzz`
   - Check that Whisper model is loaded

3. **"No speech detected"**
   - Ensure audio file contains speech
   - Try different audio format (WAV recommended)
   - Check audio file is not corrupted

4. **"Translation failed"**
   - Check that glossary CSV file exists
   - Verify file permissions

### Dependencies
```bash
pip install faster-whisper pydub rapidfuzz flask-restx requests
```

## 🎯 Testing Workflow

1. **Start with sample files:**
   ```bash
   python test_audio_upload.py --list-samples
   python test_audio_upload.py "Backend & NLP/clips/Headache/I'm sorry to hear about the pain. Where exactly is the headache—front, back, sides, left or right.mp3"
   ```

2. **Test with your own audio:**
   - Record a short audio describing symptoms
   - Upload via web interface or command line
   - Check results for accuracy

3. **Verify medical detection:**
   - Try different symptom combinations
   - Test with Arrernte and English audio
   - Check follow-up questions are relevant

## 📞 Support

For issues or questions:
1. Check the API documentation: `ARRERNTEAUDIO_API_DOCUMENTATION.md`
2. Review the Flask app logs for error messages
3. Test with sample audio files first
4. Ensure all dependencies are installed

---

**Happy Testing! 🎤✨**

