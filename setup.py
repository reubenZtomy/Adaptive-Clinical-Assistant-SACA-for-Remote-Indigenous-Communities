#!/usr/bin/env python3
"""
SwinSACA Setup Script

This script helps set up the SwinSACA project for development and production.
It handles both backend and frontend setup.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, cwd=None, shell=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=shell, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error output: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command {command}: {e}")
        return False

def setup_backend():
    """Set up the backend Python environment"""
    print("Setting up backend...")
    
    backend_dir = Path("Backend & NLP")
    if not backend_dir.exists():
        print("Backend directory not found!")
        return False
    
    # Check if Python is available
    if not run_command("python --version"):
        print("Python not found! Please install Python 3.8+ first.")
        return False
    
    # Install requirements
    print("Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt", cwd=backend_dir):
        print("Failed to install Python dependencies!")
        return False
    
    # Download NLTK data
    print("Downloading NLTK data...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        print("NLTK data downloaded successfully.")
    except Exception as e:
        print(f"Warning: Could not download NLTK data: {e}")
    
    print("Backend setup completed!")
    return True

def setup_frontend():
    """Set up the frontend Node.js environment"""
    print("Setting up frontend...")
    
    frontend_dir = Path("Frontend")
    if not frontend_dir.exists():
        print("Frontend directory not found!")
        return False
    
    # Check if Node.js is available
    if not run_command("node --version"):
        print("Node.js not found! Please install Node.js 16+ first.")
        return False
    
    if not run_command("npm --version"):
        print("npm not found! Please install npm first.")
        return False
    
    # Install dependencies
    print("Installing Node.js dependencies...")
    if not run_command("npm install", cwd=frontend_dir):
        print("Failed to install Node.js dependencies!")
        return False
    
    print("Frontend setup completed!")
    return True

def create_env_file():
    """Create a sample .env file"""
    print("Creating environment file...")
    
    env_content = """# SwinSACA Environment Configuration

# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this-in-production
JWT_SECRET_KEY=jwt-secret-string-change-this-in-production

# Database Configuration
DATABASE_URL=sqlite:///swinsaca.db

# Optional: Whisper Model Configuration
WHISPER_MODEL=base.en

# Optional: CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
"""
    
    env_file = Path("Backend & NLP/.env")
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("Created .env file in Backend & NLP directory.")
    else:
        print(".env file already exists, skipping creation.")

def create_start_scripts():
    """Create start scripts for easy running"""
    print("Creating start scripts...")
    
    # Backend start script
    backend_script = """@echo off
echo Starting SwinSACA Backend...
cd "Backend & NLP"
python app.py
pause
"""
    
    with open("start_backend.bat", 'w') as f:
        f.write(backend_script)
    
    # Frontend start script
    frontend_script = """@echo off
echo Starting SwinSACA Frontend...
cd Frontend
npm run dev
pause
"""
    
    with open("start_frontend.bat", 'w') as f:
        f.write(frontend_script)
    
    # Linux/Mac start scripts
    backend_script_sh = """#!/bin/bash
echo "Starting SwinSACA Backend..."
cd "Backend & NLP"
python app.py
"""
    
    with open("start_backend.sh", 'w') as f:
        f.write(backend_script_sh)
    
    frontend_script_sh = """#!/bin/bash
echo "Starting SwinSACA Frontend..."
cd Frontend
npm run dev
"""
    
    with open("start_frontend.sh", 'w') as f:
        f.write(frontend_script_sh)
    
    # Make shell scripts executable on Unix systems
    if platform.system() != "Windows":
        os.chmod("start_backend.sh", 0o755)
        os.chmod("start_frontend.sh", 0o755)
    
    print("Start scripts created!")

def main():
    """Main setup function"""
    print("SwinSACA Setup Script")
    print("====================")
    print()
    
    # Check if we're in the right directory
    if not Path("Backend & NLP").exists() or not Path("Frontend").exists():
        print("Error: Please run this script from the project root directory.")
        print("The directory should contain both 'Backend & NLP' and 'Frontend' folders.")
        return False
    
    success = True
    
    # Setup backend
    if not setup_backend():
        success = False
    
    print()
    
    # Setup frontend
    if not setup_frontend():
        success = False
    
    print()
    
    # Create environment file
    create_env_file()
    
    print()
    
    # Create start scripts
    create_start_scripts()
    
    print()
    
    if success:
        print("🎉 Setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Start the backend: Run 'start_backend.bat' (Windows) or './start_backend.sh' (Linux/Mac)")
        print("2. Start the frontend: Run 'start_frontend.bat' (Windows) or './start_frontend.sh' (Linux/Mac)")
        print("3. Open your browser and go to http://localhost:3000")
        print()
        print("Backend API will be available at: http://localhost:5000")
        print("API Documentation: http://localhost:5000/apidocs/")
    else:
        print("❌ Setup completed with errors. Please check the messages above.")
        return False
    
    return True

if __name__ == "__main__":
    main()
