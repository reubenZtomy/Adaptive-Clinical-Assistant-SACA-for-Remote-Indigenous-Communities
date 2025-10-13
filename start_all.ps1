# --- CONFIG ---
$PS_EXE      = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$VENV_PY     = 'F:\SwinSACA\.venv\Scripts\python.exe'
$FRONTEND    = 'F:\SwinSACA\Frontend'
$API_DIR     = 'F:\SwinSACA\NLP\API_Endpoints'

# --- Sanity ---
if (!(Test-Path $VENV_PY)) { Write-Error "Venv python not found: $VENV_PY"; exit 1 }
if (!(Test-Path $FRONTEND)) { Write-Error "Missing: $FRONTEND"; exit 1 }
if (!(Test-Path $API_DIR)) { Write-Error "Missing: $API_DIR"; exit 1 }

# Frontend (npm)
Start-Process -FilePath $PS_EXE `
  -WorkingDirectory $FRONTEND `
  -ArgumentList @('-NoExit','-Command','cmd /c "npm start"')

# Flask API (venv python)
Start-Process -FilePath $PS_EXE `
  -WorkingDirectory $API_DIR `
  -ArgumentList @('-NoExit','-Command', "& `"$VENV_PY`" app.py")

