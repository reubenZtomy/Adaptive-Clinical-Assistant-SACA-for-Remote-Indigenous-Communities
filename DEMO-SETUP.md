# SwinSACA Demo Setup Guide

This guide will help you set up and run the SwinSACA demo with all ML APIs integrated.

## 🚀 Quick Start

### Option 1: PowerShell Script (Recommended)
```powershell
# Run from project root directory
.\start-demo.ps1
```

### Option 2: Batch File
```cmd
# Run from project root directory
start-demo.bat
```

### Option 3: Manual Setup
```powershell
# Navigate to Backend & NLP directory
cd "Backend & NLP"

# Activate virtual environment
.venv\Scripts\activate

# Start the Flask server
python app.py
```

## 📋 What the Scripts Do

The demo setup scripts will:

1. **Check Python Installation** - Verify Python 3.8+ is installed
2. **Setup Virtual Environment** - Create/activate Python virtual environment
3. **Install Dependencies** - Install all required Python packages:
   - Flask, Flask-RESTx, Flask-CORS
   - ML libraries: scikit-learn, xgboost, joblib
   - Audio processing: faster-whisper, pydub, pyttsx3
   - Text processing: rapidfuzz, numpy
4. **Verify ML Models** - Check that all ML model files are present
5. **Start Flask Server** - Launch the backend with all APIs

## 🌐 Available Services

Once started, the following services will be available:

### Backend APIs
- **Main Server**: http://localhost:5000
- **API Documentation**: http://localhost:5000/ (Swagger UI)
- **Health Check**: http://localhost:5000/health

### Chat & ML APIs
- **Chat API**: http://localhost:5000/api/chat/
- **ML1 API**: http://localhost:5000/api/ml1/predict
- **ML2 API**: http://localhost:5000/api/ml2/predict
- **Fusion API**: http://localhost:5000/api/fusion/compare

## 🧪 Testing the APIs

### Test Health Check
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/health" -Method GET
```

### Test Chat API
```powershell
$headers = @{"Content-Type"="application/json"; "Origin"="http://localhost:5173"}
$body = '{"message": "I have a severe headache", "reset": false, "_context": {"language": "en", "mode": "text"}}'
Invoke-WebRequest -Uri "http://localhost:5000/api/chat/" -Method POST -Headers $headers -Body $body
```

### Test ML1 API
```powershell
$headers = @{"Content-Type"="application/json"}
$body = '{"input": "I have severe headache and nausea for two days", "topk": 3}'
Invoke-WebRequest -Uri "http://localhost:5000/api/ml1/predict" -Method POST -Headers $headers -Body $body
```

### Test ML2 API
```powershell
$headers = @{"Content-Type"="application/json"}
$body = '{"input": "I have severe headache and nausea for two days"}'
Invoke-WebRequest -Uri "http://localhost:5000/api/ml2/predict" -Method POST -Headers $headers -Body $body
```

### Test Fusion API
```powershell
$headers = @{"Content-Type"="application/json"}
$body = '{"input": "I have severe headache and nausea for two days", "topk": 3}'
Invoke-WebRequest -Uri "http://localhost:5000/api/fusion/compare" -Method POST -Headers $headers -Body $body
```

## 🎯 Demo Features

### ✅ What's Working
- **Real-time Chat**: Interactive conversation with the medical assistant
- **ML-Powered Predictions**: Real disease predictions from trained models
- **Multi-language Support**: English and Arrernte language support
- **Audio Processing**: Voice input/output capabilities
- **CORS Enabled**: Frontend can communicate with backend
- **API Documentation**: Swagger UI for testing APIs

### 🔧 ML Integration
- **ML1**: Severity assessment and disease classification
- **ML2**: Q-learning based disease prediction
- **Fusion**: Combines ML1 and ML2 results for final decision
- **Summary Generation**: Converts conversation to ML model input

## 🚨 Troubleshooting

### Common Issues

1. **Python Not Found**
   - Install Python 3.8+ from https://python.org
   - Make sure Python is added to PATH

2. **Virtual Environment Issues**
   - Delete `.venv` folder and run script again
   - Make sure you have write permissions

3. **ML Model Files Missing**
   - Check that all model files are in correct locations
   - ML1: `Backend & NLP/Ml model-1/artifacts/saca-triage-v1/`
   - ML2: `Backend & NLP/Ml model-2/model_components/`

4. **Port 5000 Already in Use**
   - Stop other services using port 5000
   - Or modify the port in `app.py`

5. **CORS Errors**
   - Make sure frontend is running on http://localhost:5173
   - Or update CORS settings in `app.py`

### Script Options

#### PowerShell Script Options
```powershell
# Skip dependency installation (faster startup)
.\start-demo.ps1 -SkipDependencies

# Show help
.\start-demo.ps1 -Help
```

## 📱 Frontend Integration

To complete the demo:

1. **Start Frontend Server**
   ```bash
   # In your frontend directory
   npm start
   # or
   yarn start
   ```

2. **Configure Frontend**
   - Make sure frontend points to `http://localhost:5000`
   - Update API endpoints if needed

3. **Test Full Integration**
   - Open frontend in browser
   - Start a conversation
   - Watch ML predictions in action!

## 🎉 Success Indicators

You'll know everything is working when:

- ✅ Backend server starts without errors
- ✅ Health check returns `{"status": "ok"}`
- ✅ Chat API responds with proper JSON
- ✅ ML APIs return predictions (not errors)
- ✅ Frontend can communicate with backend
- ✅ Disease predictions appear in chat responses

## 📞 Support

If you encounter issues:

1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure ML model files are present
4. Test individual APIs using the examples above
5. Check that ports 5000 and 5173 are available

---

**Happy Demo-ing! 🚀**

The SwinSACA system is now ready to showcase AI-powered medical assistance for remote Indigenous communities.


