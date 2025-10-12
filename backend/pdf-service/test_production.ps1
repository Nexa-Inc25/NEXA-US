# Quick test script for production Universal Standards endpoints
Write-Host "🧪 Testing Universal Standards on Production" -ForegroundColor Cyan
Write-Host ""

# Test utility detection (San Francisco → PG&E)
Write-Host "📍 Testing GPS Detection (San Francisco)..." -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "https://nexa-us-pro.onrender.com/api/utilities/detect" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"lat": 37.7749, "lng": -122.4194}' `
    -UseBasicParsing

if ($response.StatusCode -eq 200) {
    $data = $response.Content | ConvertFrom-Json
    Write-Host "   ✅ Detected: $($data.utility_id)" -ForegroundColor Green
    Write-Host "   Utility: $($data.utility_info.name)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Failed: $($response.StatusCode)" -ForegroundColor Red
}

Write-Host ""
Write-Host "📍 Testing GPS Detection (Miami)..." -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "https://nexa-us-pro.onrender.com/api/utilities/detect" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"lat": 25.7617, "lng": -80.1918}' `
    -UseBasicParsing

if ($response.StatusCode -eq 200) {
    $data = $response.Content | ConvertFrom-Json
    Write-Host "   ✅ Detected: $($data.utility_id)" -ForegroundColor Green
    Write-Host "   Utility: $($data.utility_info.name)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Failed: $($response.StatusCode)" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 Testing Utility List..." -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "https://nexa-us-pro.onrender.com/api/utilities/list" `
    -Method GET `
    -UseBasicParsing

if ($response.StatusCode -eq 200) {
    $data = $response.Content | ConvertFrom-Json
    Write-Host "   ✅ Found $($data.total) utilities:" -ForegroundColor Green
    foreach ($utility in $data.utilities) {
        Write-Host "      - $($utility.name) ($($utility.region))" -ForegroundColor Gray
    }
} else {
    Write-Host "   ❌ Failed: $($response.StatusCode)" -ForegroundColor Red
}

Write-Host ""
Write-Host "✅ Production test complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Full test suite: python tests\test_universal.py prod" -ForegroundColor Cyan
