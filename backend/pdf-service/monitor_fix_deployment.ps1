# Monitor Critical Fix Deployment
Write-Host "🚨 MONITORING CRITICAL FIX DEPLOYMENT" -ForegroundColor Red
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host ""
Write-Host "Fix: Removed asyncpg (Python 3.12 incompatibility)" -ForegroundColor Yellow
Write-Host "Commit: d56f3a7" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date
$maxWaitMinutes = 15
$checkInterval = 30
$baseUrl = "https://nexa-us-pro.onrender.com"

Write-Host "⏳ Deployment started at: $($startTime.ToString('HH:mm:ss'))" -ForegroundColor Yellow
Write-Host "   Checking every $checkInterval seconds..." -ForegroundColor Gray
Write-Host ""

$deploymentComplete = $false

while (-not $deploymentComplete) {
    $elapsed = (Get-Date) - $startTime
    $elapsedMinutes = [math]::Round($elapsed.TotalMinutes, 1)
    
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Checking build status ($elapsedMinutes min elapsed)..." -ForegroundColor Gray
    
    # Check if service is healthy
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/health" `
            -Method GET `
            -UseBasicParsing `
            -ErrorAction SilentlyContinue
        
        if ($response.StatusCode -eq 200) {
            Write-Host "   Service is responding, checking auth..." -ForegroundColor Gray
            
            # Check if auth endpoint is available
            try {
                $loginBody = @{
                    email = "admin@nexa.com"
                    password = "admin123"
                } | ConvertTo-Json
                
                $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
                    -Method POST `
                    -ContentType "application/json" `
                    -Body $loginBody `
                    -ErrorAction SilentlyContinue
                
                if ($loginResponse.access_token) {
                    Write-Host ""
                    Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
                    Write-Host "=" * 60 -ForegroundColor Gray
                    Write-Host "✅ Build completed without asyncpg error" -ForegroundColor Green
                    Write-Host "✅ uvicorn started successfully" -ForegroundColor Green
                    Write-Host "✅ Authentication working" -ForegroundColor Green
                    
                    # Test Universal Standards
                    Write-Host ""
                    Write-Host "🌍 Testing Universal Standards..." -ForegroundColor Yellow
                    $utilResponse = Invoke-RestMethod -Uri "$baseUrl/api/utilities/list" -Method GET
                    Write-Host "   ✅ Found $($utilResponse.total) utilities" -ForegroundColor Green
                    
                    Write-Host ""
                    Write-Host "📊 Deployment Summary:" -ForegroundColor Cyan
                    Write-Host "   - Build: ✅ Fixed (no asyncpg error)" -ForegroundColor White
                    Write-Host "   - Service: ✅ Running" -ForegroundColor White
                    Write-Host "   - Auth: ✅ Working" -ForegroundColor White
                    Write-Host "   - Universal Standards: ✅ Working" -ForegroundColor White
                    Write-Host "   - Deployment Time: $elapsedMinutes minutes" -ForegroundColor White
                    
                    $deploymentComplete = $true
                }
            }
            catch {
                Write-Host "   Auth not ready yet..." -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "   Service still building/deploying..." -ForegroundColor Gray
    }
    
    if ($elapsed.TotalMinutes -gt $maxWaitMinutes) {
        Write-Host ""
        Write-Host "⚠️ Timeout after $maxWaitMinutes minutes" -ForegroundColor Yellow
        Write-Host "Check Render logs for build status:" -ForegroundColor Cyan
        Write-Host "https://dashboard.render.com" -ForegroundColor White
        Write-Host ""
        Write-Host "Look for:" -ForegroundColor Yellow
        Write-Host "  - asyncpg build error (should NOT appear)" -ForegroundColor White
        Write-Host "  - uvicorn not found (should NOT appear)" -ForegroundColor White
        Write-Host "  - Successful pip install completion" -ForegroundColor White
        break
    }
    
    if (-not $deploymentComplete) {
        Start-Sleep -Seconds $checkInterval
    }
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
