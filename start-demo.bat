@echo off
REM SwinSACA Demo Startup Script (Batch version)
REM This script sets up and starts all services needed for the demo

echo [%time%] Starting SwinSACA Demo Setup...

REM Check if we're in the right directory
if not exist "Backend & NLP" (
    echo ERROR: 'Backend & NLP' directory not found. Please run this script from the project root directory.
    pause
    exit /b 1
)

echo [%time%] Project Root: %CD%

REM Check Python installation
echo [%time%] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)
echo [%time%] Python found

REM Setup virtual environment
echo [%time%] Setting up virtual environment...
if not exist "Backend & NLP\.venv" (
    echo [%time%] Creating virtual environment...
    python -m venv "Backend & NLP\.venv"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [%time%] Virtual environment created
) else (
    echo [%time%] Virtual environment already exists
)

REM Activate virtual environment and install dependencies
echo [%time%] Activating virtual environment and installing dependencies...
call "Backend & NLP\.venv\Scripts\activate.bat"

echo [%time%] Installing/updating Python dependencies...
python -m pip install --upgrade pip
pip install flask flask-restx flask-cors requests numpy scikit-learn joblib xgboost faster-whisper pydub pyttsx3 rapidfuzz

REM Check ML model files
echo [%time%] Checking ML model files...
if exist "Backend & NLP\Ml model-1\artifacts\saca-triage-v1\tfidf.pkl" (
    echo [%time%] ML1 model files found
) else (
    echo [%time%] WARNING: Some ML1 model files are missing
)

if exist "Backend & NLP\Ml model-2\model_components\vectorizer.pkl" (
    echo [%time%] ML2 model files found
) else (
    echo [%time%] WARNING: Some ML2 model files are missing
)

REM Start the Flask server
echo [%time%] Starting Flask server with all ML APIs...
echo [%time%] Server will be available at: http://localhost:5000
echo [%time%] API Documentation: http://localhost:5000/
echo.
echo [%time%] Available API Endpoints:
echo   • Chat API: http://localhost:5000/api/chat/
echo   • ML1 API: http://localhost:5000/api/ml1/predict
echo   • ML2 API: http://localhost:5000/api/ml2/predict
echo   • Fusion API: http://localhost:5000/api/fusion/compare
echo   • Health Check: http://localhost:5000/health
echo.
echo [%time%] Press Ctrl+C to stop the server
echo.

REM Change to Backend directory and start the server
cd "Backend & NLP"
python app.py

REM Return to project root
cd ..

echo [%time%] Demo setup complete!
echo.
echo [%time%] Next steps for full demo:
echo 1. Start your frontend development server (usually npm start or yarn start)
echo 2. Open your frontend application in a web browser
echo 3. Test the chat functionality with the ML-powered disease prediction
echo.
echo [%time%] The backend is now running with all ML APIs integrated!
pause


