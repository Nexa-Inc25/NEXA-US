# Install missing dependencies for Mobile App

Write-Host "Installing missing mobile dependencies..." -ForegroundColor Cyan

# Navigate to mobile directory
Set-Location C:\Users\mikev\CascadeProjects\nexa-inc-mvp\nexa-core\apps\mobile

# Install expo-barcode-scanner
Write-Host "`nInstalling expo-barcode-scanner..." -ForegroundColor Yellow
npm install expo-barcode-scanner

# Also ensure other camera-related packages are installed
Write-Host "`nEnsuring camera packages are installed..." -ForegroundColor Yellow
npm install expo-camera expo-image-picker

# Make sure AsyncStorage is installed
Write-Host "`nEnsuring AsyncStorage is installed..." -ForegroundColor Yellow
npm install @react-native-async-storage/async-storage

# Install axios if not already present
Write-Host "`nEnsuring axios is installed..." -ForegroundColor Yellow
npm install axios

Write-Host "`nDependencies installed!" -ForegroundColor Green
Write-Host "`nRun 'npm start' to test the mobile app" -ForegroundColor Cyan
