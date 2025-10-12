# Deploy GF Dashboard to Render
Write-Host "🚀 DEPLOYING GF DASHBOARD TO RENDER" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Step 1: Ensure we have the serve dependency
Write-Host "`n📦 Installing serve dependency..." -ForegroundColor Yellow
Set-Location nexa-core/apps/web
npm install serve --save

# Step 2: Test build locally
Write-Host "`n🔨 Testing build locally..." -ForegroundColor Yellow
npm run build

if (Test-Path "build/index.html") {
    Write-Host "✅ Build successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Build failed - fix errors before deploying" -ForegroundColor Red
    exit 1
}

# Step 3: Commit and push
Write-Host "`n📤 Pushing to GitHub..." -ForegroundColor Yellow
Set-Location ../../..
git add -A
git commit -m "Deploy GF Dashboard for job package workflow"
git push origin main

Write-Host "`n✅ Code pushed to GitHub!" -ForegroundColor Green

# Step 4: Deployment instructions
Write-Host "`n" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host "    DEPLOY ON RENDER.COM (2 minutes)       " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host "`n📝 STEPS:" -ForegroundColor Yellow
Write-Host "1. Go to https://dashboard.render.com" -ForegroundColor White
Write-Host "2. Click 'New +' → 'Static Site'" -ForegroundColor White
Write-Host "3. Connect your GitHub repo (nexa-inc-mvp)" -ForegroundColor White
Write-Host "`n4. Configure:" -ForegroundColor Yellow
Write-Host "   Name: gf-dashboard" -ForegroundColor Green
Write-Host "   Branch: main" -ForegroundColor Green
Write-Host "   Root Directory: nexa-core/apps/web" -ForegroundColor Green
Write-Host "   Build Command: npm install && npm run build" -ForegroundColor Green
Write-Host "   Publish Directory: build" -ForegroundColor Green

Write-Host "`n5. Environment Variables:" -ForegroundColor Yellow
Write-Host "   REACT_APP_API_URL = https://nexa-doc-analyzer-oct2025.onrender.com" -ForegroundColor Green

Write-Host "`n6. Click 'Create Static Site'" -ForegroundColor Cyan

Write-Host "`n🎉 Your dashboard will be live at:" -ForegroundColor Green
Write-Host "   https://gf-dashboard.onrender.com" -ForegroundColor Cyan

Write-Host "`n📊 TEST THE COMPLETE WORKFLOW:" -ForegroundColor Yellow
Write-Host "1. Access dashboard at the URL above" -ForegroundColor White
Write-Host "2. Login as 'general_foreman'" -ForegroundColor White
Write-Host "3. Upload PG&E Greenbook via API" -ForegroundColor White
Write-Host "4. Upload audit document" -ForegroundColor White
Write-Host "5. See repealable infractions with confidence & reasons" -ForegroundColor White

# Open Render in browser
$openRender = Read-Host "`nOpen Render.com now? (y/n)"
if ($openRender -eq 'y') {
    Start-Process "https://dashboard.render.com/select-repo?type=static"
}
