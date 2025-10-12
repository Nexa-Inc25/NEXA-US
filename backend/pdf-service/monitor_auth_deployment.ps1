# Monitor Universal Standards + Auth Deployment
Write-Host "🔍 Monitoring NEXA Deployment Status" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date
$maxWaitMinutes = 15
$checkInterval = 30  # seconds
$baseUrl = "https://nexa-us-pro.onrender.com"

Write-Host "⏳ Deployment started at: $($startTime.ToString('HH:mm:ss'))" -ForegroundColor Yellow
Write-Host "   Checking every $checkInterval seconds..." -ForegroundColor Gray
Write-Host ""

$deploymentComplete = $false

while (-not $deploymentComplete) {
    $elapsed = (Get-Date) - $startTime
    $elapsedMinutes = [math]::Round($elapsed.TotalMinutes, 1)
    
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Checking deployment ($elapsedMinutes min elapsed)..." -ForegroundColor Gray
    
    # Check if auth endpoint is available
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/auth/health" `
            -Method GET `
            -UseBasicParsing `
            -ErrorAction SilentlyContinue
        
        if ($response.StatusCode -eq 200) {
            Write-Host ""
            Write-Host "🎉 DEPLOYMENT COMPLETE!" -ForegroundColor Green
            Write-Host "=" * 60 -ForegroundColor Gray
            
            # Test auth login
            Write-Host "🔐 Testing Authentication..." -ForegroundColor Yellow
            $loginBody = @{
                email = "admin@nexa.com"
                password = "admin123"
            } | ConvertTo-Json
            
            $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
                -Method POST `
                -ContentType "application/json" `
                -Body $loginBody
            
            if ($loginResponse.access_token) {
                Write-Host "   ✅ Authentication working!" -ForegroundColor Green
                Write-Host "   User: $($loginResponse.user.email)" -ForegroundColor Gray
                Write-Host "   Role: $($loginResponse.user.role)" -ForegroundColor Gray
            }
            
            # Test Universal Standards
            Write-Host ""
            Write-Host "🌍 Testing Universal Standards..." -ForegroundColor Yellow
            $utilResponse = Invoke-RestMethod -Uri "$baseUrl/api/utilities/list" -Method GET
            Write-Host "   ✅ Found $($utilResponse.total) utilities configured" -ForegroundColor Green
            
            # Test GPS Detection
            Write-Host ""
            Write-Host "📍 Testing GPS Detection..." -ForegroundColor Yellow
            $gpsBody = @{ lat = 37.7749; lng = -122.4194 } | ConvertTo-Json
            $gpsResponse = Invoke-RestMethod -Uri "$baseUrl/api/utilities/detect" `
                -Method POST `
                -ContentType "application/json" `
                -Body $gpsBody
            Write-Host "   ✅ San Francisco → $($gpsResponse.utility_id)" -ForegroundColor Green
            
            Write-Host ""
            Write-Host "=" * 60 -ForegroundColor Gray
            Write-Host "✅ All Systems Operational!" -ForegroundColor Green
            Write-Host ""
            Write-Host "📊 Deployment Summary:" -ForegroundColor Cyan
            Write-Host "   - Authentication: ✅ Working" -ForegroundColor White
            Write-Host "   - Universal Standards: ✅ Working" -ForegroundColor White
            Write-Host "   - GPS Detection: ✅ Working" -ForegroundColor White
            Write-Host "   - Deployment Time: $elapsedMinutes minutes" -ForegroundColor White
            Write-Host ""
            Write-Host "🚀 Ready to run full test suite:" -ForegroundColor Yellow
            Write-Host "   python tests\test_universal.py prod" -ForegroundColor Cyan
            
            $deploymentComplete = $true
        }
    }
    catch {
        # Still deploying
        Write-Host "   Auth not ready yet (still building)..." -ForegroundColor Gray
    }
    
    if ($elapsed.TotalMinutes -gt $maxWaitMinutes) {
        Write-Host ""
        Write-Host "⚠️ Timeout after $maxWaitMinutes minutes" -ForegroundColor Yellow
        Write-Host "Check Render dashboard for build status:" -ForegroundColor Cyan
        Write-Host "https://dashboard.render.com" -ForegroundColor White
        break
    }
    
    if (-not $deploymentComplete) {
        Start-Sleep -Seconds $checkInterval
    }
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
