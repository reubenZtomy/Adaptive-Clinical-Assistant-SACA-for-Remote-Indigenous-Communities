# SwinSACA Demo Test Script
# This script tests all the APIs to ensure they're working correctly

Write-Host "SwinSACA Demo API Test" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green
Write-Host ""

$baseUrl = "http://localhost:5000"

# Test 1: Health Check
Write-Host "1. Testing Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✓ Health check passed" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Health check failed (Status: $($response.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: ML1 API
Write-Host "2. Testing ML1 API..." -ForegroundColor Yellow
try {
    $headers = @{"Content-Type"="application/json"}
    $body = '{"input": "I have severe headache and nausea for two days", "topk": 3}'
    $response = Invoke-WebRequest -Uri "$baseUrl/api/ml1/predict" -Method POST -Headers $headers -Body $body -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   ✓ ML1 API working - Severity: $($data.severity), Confidence: $([math]::Round($data.confidence, 3))" -ForegroundColor Green
    } else {
        Write-Host "   ✗ ML1 API failed (Status: $($response.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ ML1 API failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: ML2 API
Write-Host "3. Testing ML2 API..." -ForegroundColor Yellow
try {
    $headers = @{"Content-Type"="application/json"}
    $body = '{"input": "I have severe headache and nausea for two days"}'
    $response = Invoke-WebRequest -Uri "$baseUrl/api/ml2/predict" -Method POST -Headers $headers -Body $body -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   ✓ ML2 API working - Predicted: $($data.predicted_label), Probability: $([math]::Round($data.probability, 3))" -ForegroundColor Green
    } else {
        Write-Host "   ✗ ML2 API failed (Status: $($response.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ ML2 API failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Fusion API
Write-Host "4. Testing Fusion API..." -ForegroundColor Yellow
try {
    $headers = @{"Content-Type"="application/json"}
    $body = '{"input": "I have severe headache and nausea for two days", "topk": 3}'
    $response = Invoke-WebRequest -Uri "$baseUrl/api/fusion/compare" -Method POST -Headers $headers -Body $body -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   ✓ Fusion API working - Final: $($data.final.disease_label), Severity: $($data.final.severity)" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Fusion API failed (Status: $($response.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Fusion API failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Chat API
Write-Host "5. Testing Chat API..." -ForegroundColor Yellow
try {
    $headers = @{"Content-Type"="application/json"; "Origin"="http://localhost:5173"}
    $body = '{"message": "I have a severe headache", "reset": false, "_context": {"language": "en", "mode": "text"}}'
    $response = Invoke-WebRequest -Uri "$baseUrl/api/chat/" -Method POST -Headers $headers -Body $body -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   ✓ Chat API working - Bot replied: $($data.reply.Substring(0, [Math]::Min(50, $data.reply.Length)))..." -ForegroundColor Green
    } else {
        Write-Host "   ✗ Chat API failed (Status: $($response.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Chat API failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Demo API Test Complete!" -ForegroundColor Green
Write-Host "If all tests passed, your SwinSACA demo is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start your frontend development server" -ForegroundColor White
Write-Host "2. Open your frontend application in a web browser" -ForegroundColor White
Write-Host "3. Test the complete chat experience with ML predictions" -ForegroundColor White


