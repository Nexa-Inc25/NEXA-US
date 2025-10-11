# Install missing React Navigation and other dependencies
Write-Host "📦 Installing missing dependencies..." -ForegroundColor Cyan

cd mobile

# Install React Navigation
Write-Host "`n📱 Installing React Navigation..." -ForegroundColor Yellow
npm install @react-navigation/native @react-navigation/bottom-tabs @react-navigation/stack --legacy-peer-deps

# Install peer dependencies for React Navigation
Write-Host "`n📱 Installing React Navigation dependencies..." -ForegroundColor Yellow
npm install react-native-screens react-native-safe-area-context react-native-gesture-handler --legacy-peer-deps

# Install expo-linear-gradient
Write-Host "`n🎨 Installing expo-linear-gradient..." -ForegroundColor Yellow
npm install expo-linear-gradient --legacy-peer-deps

# Install expo-constants
Write-Host "`n📱 Installing expo-constants..." -ForegroundColor Yellow
npm install expo-constants --legacy-peer-deps

Write-Host "`n✅ Dependencies installed!" -ForegroundColor Green
