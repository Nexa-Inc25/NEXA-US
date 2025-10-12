# NEXA Live Deployment Test Script (PowerShell)
# Tests the production system at https://nexa-us-pro.onrender.com

$URL = "https://nexa-us-pro.onrender.com"

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "   NEXA LIVE DEPLOYMENT TEST" -ForegroundColor Yellow
Write-Host "   URL: $URL" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Test 1: Health Check
Write-Host "Test 1: Health Check" -ForegroundColor Green
try {
    $health = Invoke-RestMethod -Uri "$URL/health" -Method Get
    $health | ConvertTo-Json
    Write-Host "✓ Health check passed" -ForegroundColor Green
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 2: Root Endpoint
Write-Host "Test 2: System Info" -ForegroundColor Green
try {
    $info = Invoke-RestMethod -Uri "$URL/" -Method Get
    $info | ConvertTo-Json
    Write-Host "✓ System info retrieved" -ForegroundColor Green
} catch {
    Write-Host "✗ System info failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Get Auth Token (Skip if auth not enabled)
Write-Host "Test 3: Authentication" -ForegroundColor Green
$token = ""
try {
    $body = @{
        username = "admin"
        password = "Test@Pass123!"
    }
    $tokenResponse = Invoke-RestMethod -Uri "$URL/auth/token" -Method Post -Body $body
    $token = $tokenResponse.access_token
    
    if ($token) {
        Write-Host "✓ Token obtained successfully" -ForegroundColor Green
        Write-Host "Token (first 20 chars): $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Cyan
    } else {
        Write-Host "⚠ No token in response (auth might be disabled)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Authentication skipped (might be disabled): $_" -ForegroundColor Yellow
}
Write-Host ""

# Test 4: Check Spec Library
Write-Host "Test 4: Spec Library Status" -ForegroundColor Green
try {
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    $specLibrary = Invoke-RestMethod -Uri "$URL/spec-library" -Method Get -Headers $headers
    $specLibrary | ConvertTo-Json
    Write-Host "✓ Spec library accessed" -ForegroundColor Green
} catch {
    Write-Host "✗ Spec library failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 5: ML Status
Write-Host "Test 5: ML System Status" -ForegroundColor Green
try {
    $mlStatus = Invoke-RestMethod -Uri "$URL/ml-status" -Method Get -Headers $headers
    $mlStatus | ConvertTo-Json -Depth 3
    Write-Host "✓ ML status retrieved" -ForegroundColor Green
} catch {
    Write-Host "✗ ML status failed: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "✓ Basic tests complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Upload a spec PDF using:" -ForegroundColor White
Write-Host '   $headers = @{"Authorization" = "Bearer $token"}' -ForegroundColor Gray
Write-Host '   Invoke-RestMethod -Uri "$URL/upload-specs" -Method Post -Headers $headers -Form @{files = Get-Item "spec.pdf"}' -ForegroundColor Gray
Write-Host ""
Write-Host "2. Analyze an audit PDF using:" -ForegroundColor White
Write-Host '   Invoke-RestMethod -Uri "$URL/analyze-audit" -Method Post -Headers $headers -Form @{file = Get-Item "audit.pdf"}' -ForegroundColor Gray
