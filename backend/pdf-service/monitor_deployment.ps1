# Monitor Render deployment status
Write-Host "🔍 Monitoring NEXA Universal Standards Deployment" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date
$maxWaitMinutes = 15
$checkInterval = 30  # seconds

Write-Host "⏳ Waiting for Render to rebuild (typically 5-10 minutes)..." -ForegroundColor Yellow
Write-Host "   Started at: $($startTime.ToString('HH:mm:ss'))" -ForegroundColor Gray
Write-Host ""

while ($true) {
    $elapsed = (Get-Date) - $startTime
    $elapsedMinutes = [math]::Round($elapsed.TotalMinutes, 1)
    
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Checking deployment status... ($elapsedMinutes min elapsed)" -ForegroundColor Gray
    
    # Test Universal Standards endpoint
    try {
        $response = Invoke-WebRequest -Uri "https://nexa-us-pro.onrender.com/api/utilities/list" `
            -Method GET `
            -UseBasicParsing `
            -ErrorAction Stop
        
        if ($response.StatusCode -eq 200) {
            Write-Host ""
            Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
            Write-Host "=" * 60 -ForegroundColor Gray
            
            $data = $response.Content | ConvertFrom-Json
            Write-Host "✅ Universal Standards Engine is LIVE!" -ForegroundColor Green
            Write-Host "   Found $($data.total) utilities configured" -ForegroundColor Cyan
            
            # Test GPS detection
            Write-Host ""
            Write-Host "📍 Testing GPS Detection..." -ForegroundColor Yellow
            $gpsResponse = Invoke-WebRequest -Uri "https://nexa-us-pro.onrender.com/api/utilities/detect" `
                -Method POST `
                -ContentType "application/json" `
                -Body '{"lat": 37.7749, "lng": -122.4194}' `
                -UseBasicParsing
            
            $gpsData = $gpsResponse.Content | ConvertFrom-Json
            Write-Host "   Detected: $($gpsData.utility_id) for San Francisco" -ForegroundColor Green
            
            Write-Host ""
            Write-Host "📊 Available Endpoints:" -ForegroundColor Cyan
            Write-Host "   POST /api/utilities/detect - GPS detection" -ForegroundColor White
            Write-Host "   POST /api/utilities/{id}/ingest - Spec ingestion" -ForegroundColor White
            Write-Host "   GET  /api/utilities/list - List utilities" -ForegroundColor White
            Write-Host "   POST /api/utilities/jobs/create - Create jobs" -ForegroundColor White
            Write-Host "   POST /api/utilities/standards/cross-reference - Cross-ref" -ForegroundColor White
            
            Write-Host ""
            Write-Host "🚀 Deployment took $elapsedMinutes minutes" -ForegroundColor Green
            Write-Host "=" * 60 -ForegroundColor Gray
            break
        }
    }
    catch {
        # Still 404, deployment not complete
        if ($elapsed.TotalMinutes -gt $maxWaitMinutes) {
            Write-Host ""
            Write-Host "⚠️ Timeout after $maxWaitMinutes minutes" -ForegroundColor Yellow
            Write-Host "Check Render dashboard: https://dashboard.render.com" -ForegroundColor Cyan
            break
        }
    }
    
    Start-Sleep -Seconds $checkInterval
}

Write-Host ""
Write-Host "💡 Next: Run test suite with:" -ForegroundColor Yellow
Write-Host "   python tests\test_universal.py prod" -ForegroundColor Cyan
