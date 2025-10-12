# NEXA Backend Deployment and Test Script

Write-Host "NEXA BACKEND DEPLOYMENT" -ForegroundColor Cyan
Write-Host ("=" * 60)

# Step 1: Commit and push
Write-Host "`nCommitting and pushing changes..." -ForegroundColor Yellow
git add -A
git commit -m "Deploy backend fixes - auth integration and spec initialization"
git push origin main

# Step 2: Wait for deployment
Write-Host "`nWaiting for Render deployment (5 minutes)..." -ForegroundColor Yellow
$wait_minutes = 5
for ($i = 1; $i -le $wait_minutes; $i++) {
    Write-Host "  Minute $i of $wait_minutes..." -ForegroundColor Gray
    Start-Sleep -Seconds 60
}

# Step 3: Test deployment
Write-Host "`nTesting deployed service..." -ForegroundColor Yellow
$baseUrl = "https://nexa-us-pro.onrender.com"

# Health check
Write-Host "`n1. Health Check..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method GET
if ($health.status -eq "healthy") {
    Write-Host "   PASS: Service is healthy" -ForegroundColor Green
} else {
    Write-Host "   FAIL: Service unhealthy" -ForegroundColor Red
}

# Auth test
Write-Host "`n2. Authentication..." -ForegroundColor Cyan
try {
    $authBody = @{
        email = "admin@nexa.com"
        password = "admin123"
    } | ConvertTo-Json

    $auth = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $authBody
    
    if ($auth.access_token) {
        Write-Host "   PASS: Authentication working" -ForegroundColor Green
        $token = $auth.access_token
    } else {
        Write-Host "   FAIL: No token received" -ForegroundColor Red
        $token = $null
    }
} catch {
    Write-Host "   FAIL: Auth endpoint not found" -ForegroundColor Red
    $token = $null
}

# Utility detection test
Write-Host "`n3. Utility Detection..." -ForegroundColor Cyan
$detectBody = @{
    location = @{
        lat = 37.7749
        lng = -122.4194
    }
} | ConvertTo-Json

$headers = @{"Content-Type" = "application/json"}
if ($token) {
    $headers["Authorization"] = "Bearer $token"
}

try {
    $detect = Invoke-RestMethod -Uri "$baseUrl/api/utilities/detect" `
        -Method POST `
        -Headers $headers `
        -Body $detectBody
    
    if ($detect.utility_id -eq "PGE") {
        Write-Host "   PASS: Detected PGE in San Francisco" -ForegroundColor Green
    } else {
        Write-Host "   PARTIAL: Got response but wrong utility" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   FAIL: Detection failed" -ForegroundColor Red
}

# Full test suite
Write-Host "`n4. Running full test suite..." -ForegroundColor Cyan
Set-Location "c:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service"
python tests\test_all_endpoints.py prod

Write-Host "`nDeployment complete." -ForegroundColor Green
