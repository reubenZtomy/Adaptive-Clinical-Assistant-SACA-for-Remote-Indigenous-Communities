Write-Host "Starting Arrernte Audio Analysis API Test Environment" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

Write-Host ""
Write-Host "1. Starting Flask API server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$(Get-Location)'; python 'Backend & NLP\app.py'"

Write-Host ""
Write-Host "2. Waiting for API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "3. Opening web interface..." -ForegroundColor Yellow
Start-Process "audio_upload_test.html"

Write-Host ""
Write-Host "4. Available test commands:" -ForegroundColor Cyan
Write-Host "   - List sample audio files: python test_audio_upload.py --list-samples" -ForegroundColor White
Write-Host "   - Test with audio file: python test_audio_upload.py 'path\to\your\audio.wav'" -ForegroundColor White
Write-Host "   - Test with forced English: python test_audio_upload.py 'path\to\your\audio.wav' --force-language en" -ForegroundColor White

Write-Host ""
Write-Host "5. Web interface opened in your browser" -ForegroundColor Cyan
Write-Host "   - Upload audio files using the web interface" -ForegroundColor White
Write-Host "   - View detailed analysis results" -ForegroundColor White
Write-Host "   - Test different audio formats" -ForegroundColor White

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")


