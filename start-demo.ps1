# SwinSACA Demo Startup Script
# This script sets up and starts all services needed for the demo

param(
    [switch]$SkipDependencies,
    [switch]$Help
)

if ($Help) {
    Write-Host "SwinSACA Demo Startup Script" -ForegroundColor Green
    Write-Host "Usage: .\start-demo.ps1 [options]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -SkipDependencies    Skip dependency installation check" -ForegroundColor White
    Write-Host "  -Help               Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "This script will:" -ForegroundColor Yellow
    Write-Host "  1. Check and install Python dependencies" -ForegroundColor White
    Write-Host "  2. Start the Flask backend server with all ML APIs" -ForegroundColor White
    Write-Host "  3. Provide instructions for starting the frontend" -ForegroundColor White
    exit 0
}

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"

function Write-Status {
    param([string]$Message, [string]$Color = $InfoColor)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Status $Message $SuccessColor
}

function Write-Error {
    param([string]$Message)
    Write-Status $Message $ErrorColor
}

function Write-Warning {
    param([string]$Message)
    Write-Status $Message $WarningColor
}

# Check if we're in the right directory
if (-not (Test-Path "Backend `& NLP")) {
    Write-Error "Error: 'Backend & NLP' directory not found. Please run this script from the project root directory."
    exit 1
}

Write-Status "Starting SwinSACA Demo Setup..." $InfoColor
Write-Status "Project Root: $(Get-Location)" $InfoColor

# Step 1: Check Python installation
Write-Status "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python found: $pythonVersion"
    } else {
        throw "Python not found"
    }
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.8+ and try again."
    exit 1
}

# Step 2: Check and setup virtual environment
Write-Status "Setting up virtual environment..."
$venvPath = "Backend `& NLP\.venv"

if (-not (Test-Path $venvPath)) {
    Write-Status "Creating virtual environment..."
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    Write-Success "Virtual environment created"
} else {
    Write-Success "Virtual environment already exists"
}

# Step 3: Activate virtual environment and install dependencies
Write-Status "Activating virtual environment and installing dependencies..."

$activateScript = "$venvPath\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment activation script not found"
    exit 1
}

# Activate virtual environment
& $activateScript

if (-not $SkipDependencies) {
    Write-Status "Installing/updating Python dependencies..."
    
    # Upgrade pip first
    python -m pip install --upgrade pip
    
    # Install required packages
    $packages = @(
        "flask",
        "flask-restx", 
        "flask-cors",
        "requests",
        "numpy",
        "scikit-learn",
        "joblib",
        "xgboost",
        "faster-whisper",
        "pydub",
        "pyttsx3",
        "rapidfuzz"
    )
    
    foreach ($package in $packages) {
        Write-Status "Installing $package..."
        pip install $package --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Success "OK $package installed"
        } else {
            Write-Warning "Failed to install $package (may already be installed)"
        }
    }
} else {
    Write-Warning "Skipping dependency installation"
}

# Step 4: Check ML model files
Write-Status "Checking ML model files..."

$ml1Path = "Backend `& NLP\Ml model-1\artifacts\saca-triage-v1"
$ml2Path = "Backend `& NLP\Ml model-2\model_components"

$requiredFiles = @(
    "$ml1Path\tfidf.pkl",
    "$ml1Path\rf.pkl", 
    "$ml1Path\xgb.pkl",
    "$ml1Path\config.json",
    "$ml2Path\vectorizer.pkl",
    "$ml2Path\kmeans.pkl",
    "$ml2Path\q_table.npy",
    "$ml2Path\label_encoder.pkl"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Success "OK $(Split-Path $file -Leaf)"
    } else {
        Write-Warning "Missing: $(Split-Path $file -Leaf)"
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Warning "Some ML model files are missing. The APIs may not work correctly."
    Write-Warning "Missing files: $($missingFiles -join ', ')"
}

# Step 5: Start the Flask server
Write-Status "Starting Flask server with all ML APIs..."
Write-Status "Server will be available at: http://localhost:5000" $InfoColor
Write-Status "API Documentation: http://localhost:5000/" $InfoColor
Write-Status ""
Write-Status "Available API Endpoints:" $InfoColor
Write-Status "  • Chat API: http://localhost:5000/api/chat/" $InfoColor
Write-Status "  • ML1 API: http://localhost:5000/api/ml1/predict" $InfoColor
Write-Status "  • ML2 API: http://localhost:5000/api/ml2/predict" $InfoColor
Write-Status "  • Fusion API: http://localhost:5000/api/fusion/compare" $InfoColor
Write-Status "  • Health Check: http://localhost:5000/health" $InfoColor
Write-Status ""
Write-Status "Press Ctrl+C to stop the server" $WarningColor
Write-Status ""

# Change to Backend & NLP directory and start the server
Set-Location "Backend `& NLP"

try {
    # Start the Flask server
    python app.py
} catch {
    Write-Error "Failed to start Flask server: $_"
    exit 1
} finally {
    # Return to project root
    Set-Location ".."
}

Write-Status "Demo setup complete!" $SuccessColor
Write-Status ""
Write-Status "Next steps for full demo:" $InfoColor
Write-Status "1. Start your frontend development server (usually npm start or yarn start)" $InfoColor
Write-Status "2. Open your frontend application in a web browser" $InfoColor
Write-Status "3. Test the chat functionality with the ML-powered disease prediction" $InfoColor
Write-Status ""
Write-Status "The backend is now running with all ML APIs integrated!" $SuccessColor