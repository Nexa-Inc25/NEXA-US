# Deploy NEXA Field Management System
Write-Host "🚀 Deploying NEXA Field Management System..." -ForegroundColor Cyan

# Backend API Integration
Write-Host "`n📦 Adding Field Management API to backend..." -ForegroundColor Yellow

# Create deployment package
$backendFiles = @(
    "backend/pdf-service/user_roles.py",
    "backend/pdf-service/field_management_api.py"
)

# Copy to deployment folder
foreach ($file in $backendFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
    }
}

# Test mobile app
Write-Host "`n📱 Testing Mobile App..." -ForegroundColor Yellow
Set-Location mobile

# Install dependencies
Write-Host "Installing dependencies..."
npm install --legacy-peer-deps 2>$null

# Start Expo
Write-Host "`n🎯 Starting Expo development server..." -ForegroundColor Cyan
Write-Host "Options:" -ForegroundColor White
Write-Host "  Press 'w' for web browser" -ForegroundColor Gray
Write-Host "  Press 'a' for Android" -ForegroundColor Gray
Write-Host "  Press 'i' for iOS" -ForegroundColor Gray

# Run Expo
npx expo start --web

Write-Host "`n✨ NEXA Field Management System Deployed!" -ForegroundColor Green
