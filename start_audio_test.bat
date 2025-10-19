@echo off
echo Starting Arrernte Audio Analysis API Test Environment
echo ====================================================

echo.
echo 1. Starting Flask API server...
start "Flask API" cmd /k "cd /d \"%~dp0\" && python \"Backend & NLP\app.py\""

echo.
echo 2. Waiting for API to start...
timeout /t 5 /nobreak > nul

echo.
echo 3. Opening web interface...
start "" "audio_upload_test.html"

echo.
echo 4. Available test commands:
echo    - List sample audio files: python test_audio_upload.py --list-samples
echo    - Test with audio file: python test_audio_upload.py "path\to\your\audio.wav"
echo    - Test with forced English: python test_audio_upload.py "path\to\your\audio.wav" --force-language en
echo.
echo 5. Web interface opened in your browser
echo    - Upload audio files using the web interface
echo    - View detailed analysis results
echo    - Test different audio formats
echo.
echo Press any key to exit...
pause > nul


