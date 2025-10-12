# PowerShell script to deploy GF Dashboard to Render
Write-Host "🚀 DEPLOYING GF DASHBOARD TO RENDER" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Step 1: Check we're in the right directory
$currentPath = Get-Location
Write-Host "Current directory: $currentPath" -ForegroundColor Yellow

# Step 2: Commit and push changes
Write-Host "`n📦 Pushing code to GitHub..." -ForegroundColor Cyan
git add -A
git commit -m "Deploy GF dashboard to production on Render"
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Code pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Git push may have failed - check if already up to date" -ForegroundColor Yellow
}

# Step 3: Show deployment instructions
Write-Host "`n" -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "    NOW GO TO RENDER.COM AND DEPLOY!        " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

Write-Host "`n📝 INSTRUCTIONS:" -ForegroundColor Yellow
Write-Host "1. Go to: https://dashboard.render.com" -ForegroundColor White
Write-Host "2. Click 'New +' → 'Web Service'" -ForegroundColor White
Write-Host "3. Select your repo: nexa-inc-mvp" -ForegroundColor White
Write-Host "`n4. Use these EXACT settings:" -ForegroundColor Yellow
Write-Host "   Name: nexa-gf-dashboard" -ForegroundColor Green
Write-Host "   Root Directory: nexa-core/apps/web" -ForegroundColor Green
Write-Host "   Build Command: npm install && npm run build" -ForegroundColor Green
Write-Host "   Start Command: npm run serve" -ForegroundColor Green
Write-Host "`n5. Environment Variables:" -ForegroundColor Yellow
Write-Host "   REACT_APP_API_URL = https://nexa-doc-analyzer-oct2025.onrender.com" -ForegroundColor Green

Write-Host "`n6. Click 'Create Web Service'" -ForegroundColor Cyan
Write-Host "`n✅ Your dashboard will be LIVE at:" -ForegroundColor Green
Write-Host "   https://nexa-gf-dashboard.onrender.com" -ForegroundColor Cyan
Write-Host "`n⏱️  Deployment takes ~5 minutes" -ForegroundColor Yellow

# Open Render in browser
Write-Host "`n🌐 Opening Render.com..." -ForegroundColor Cyan
Start-Process "https://dashboard.render.com/select-repo?type=web"
