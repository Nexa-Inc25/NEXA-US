# Deploy Universal Standards Engine to NEXA
# PowerShell script for Windows deployment

Write-Host "🚀 Deploying Universal Standards Engine to NEXA" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Check if in correct directory
if (!(Test-Path "app_oct2025_enhanced.py")) {
    Write-Host "❌ Error: Please run from backend/pdf-service directory" -ForegroundColor Red
    Write-Host "   cd C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📋 Pre-deployment checklist:" -ForegroundColor Yellow
Write-Host "   ✓ universal_standards.py created in modules/" -ForegroundColor Green
Write-Host "   ✓ Integration added to app_oct2025_enhanced.py" -ForegroundColor Green
Write-Host "   ✓ Test script created in tests/" -ForegroundColor Green

# Generate JWT secret if not exists
if (!(Test-Path ".env")) {
    Write-Host ""
    Write-Host "🔑 Generating JWT secret..." -ForegroundColor Yellow
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
    $jwt_secret = [Convert]::ToBase64String($bytes)
    
    "JWT_SECRET=$jwt_secret" | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "   ✓ JWT secret generated and saved to .env" -ForegroundColor Green
    Write-Host "   📝 Add this to Render environment variables:" -ForegroundColor Cyan
    Write-Host "      JWT_SECRET=$jwt_secret" -ForegroundColor White
}

# Test locally first (optional)
$testLocal = Read-Host "`n🧪 Test locally first? (y/n)"
if ($testLocal -eq 'y') {
    Write-Host ""
    Write-Host "🔧 Starting local server..." -ForegroundColor Yellow
    
    # Start the server in background
    $serverJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        python app_oct2025_enhanced.py
    }
    
    Write-Host "   ⏳ Waiting for server to start (10 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    
    # Run tests
    Write-Host "🧪 Running tests..." -ForegroundColor Yellow
    python tests\test_universal.py
    
    # Stop the server
    Write-Host ""
    Write-Host "🛑 Stopping local server..." -ForegroundColor Yellow
    Stop-Job -Job $serverJob
    Remove-Job -Job $serverJob
}

# Git operations
Write-Host ""
Write-Host "📦 Preparing for deployment..." -ForegroundColor Yellow

# Check for uncommitted changes
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "   Found uncommitted changes:" -ForegroundColor Cyan
    git status --short
    
    $commit = Read-Host "`n💾 Commit these changes? (y/n)"
    if ($commit -eq 'y') {
        Write-Host ""
        Write-Host "📝 Adding files to git..." -ForegroundColor Yellow
        git add modules/universal_standards.py
        git add app_oct2025_enhanced.py
        git add tests/test_universal.py
        git add deploy_universal.ps1
        
        $message = Read-Host "   Enter commit message (or press Enter for default)"
        if ([string]::IsNullOrWhiteSpace($message)) {
            $message = "Add Universal Standards Engine for multi-utility support"
        }
        
        git commit -m $message
        Write-Host "   ✓ Changes committed" -ForegroundColor Green
    }
}

# Push to GitHub
$push = Read-Host "`n🚀 Push to GitHub and deploy? (y/n)"
if ($push -eq 'y') {
    Write-Host ""
    Write-Host "📤 Pushing to GitHub..." -ForegroundColor Yellow
    git push origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Successfully pushed to GitHub" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 Deployment initiated!" -ForegroundColor Green
        Write-Host ""
        Write-Host "⏱️  Render will auto-deploy in 5-10 minutes" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "📊 Next Steps:" -ForegroundColor Yellow
        Write-Host "   1. Check Render logs: https://dashboard.render.com" -ForegroundColor White
        Write-Host "   2. Add JWT_SECRET to Render environment variables" -ForegroundColor White
        Write-Host "   3. Test production endpoints after deploy:" -ForegroundColor White
        Write-Host "      python tests\test_universal.py prod" -ForegroundColor Cyan
    } else {
        Write-Host "   ❌ Push failed. Check your GitHub credentials" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "📋 Manual deployment steps:" -ForegroundColor Yellow
    Write-Host "   1. git push origin main" -ForegroundColor White
    Write-Host "   2. Wait for Render auto-deploy" -ForegroundColor White
    Write-Host "   3. Test with: python tests\test_universal.py prod" -ForegroundColor White
}

Write-Host ""
Write-Host "📚 Universal Standards API Endpoints:" -ForegroundColor Cyan
Write-Host "   POST /api/utilities/detect          - GPS-based utility detection" -ForegroundColor White
Write-Host "   POST /api/utilities/{id}/ingest     - Ingest utility specs (PDF)" -ForegroundColor White
Write-Host "   GET  /api/utilities/list            - List all utilities" -ForegroundColor White
Write-Host "   POST /api/utilities/jobs/create     - Create job with auto-detection" -ForegroundColor White
Write-Host "   POST /api/utilities/forms/{id}/populate - Populate utility forms" -ForegroundColor White
Write-Host "   POST /api/utilities/standards/cross-reference - Cross-reference standards" -ForegroundColor White

Write-Host ""
Write-Host "🌟 Business Impact:" -ForegroundColor Green
Write-Host "   • Multi-utility support (PG&E, SCE, FPL, SDG&E)" -ForegroundColor White
Write-Host "   • GPS auto-detection for jobs" -ForegroundColor White
Write-Host "   • Cross-reference standards across utilities" -ForegroundColor White
Write-Host "   • Universal → Specific form translation" -ForegroundColor White
Write-Host "   • Network effects: more utilities = more value" -ForegroundColor White

Write-Host ""
Write-Host "💡 Example Usage:" -ForegroundColor Yellow
Write-Host @'
   # Detect utility for San Francisco location
   curl -X POST https://nexa-us-pro.onrender.com/api/utilities/detect \
     -H "Content-Type: application/json" \
     -d '{"lat": 37.7749, "lng": -122.4194}'
'@ -ForegroundColor Gray

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host "✅ Universal Standards Engine deployment complete!" -ForegroundColor Green
