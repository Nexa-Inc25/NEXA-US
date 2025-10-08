# Nexa Core - Local Development Setup Script
# Run with: .\scripts\setup-local.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NEXA CORE - LOCAL SETUP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js not found. Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version
Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green

# Check PostgreSQL
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  PostgreSQL not found. You'll need it for local dev." -ForegroundColor Yellow
    Write-Host "   Download from: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "   Or use Docker: docker run -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15" -ForegroundColor Yellow
} else {
    Write-Host "✅ PostgreSQL installed" -ForegroundColor Green
}

Write-Host ""

# Step 1: Install dependencies
Write-Host "Step 1: Installing dependencies..." -ForegroundColor Yellow
Write-Host ""

# Root dependencies
Write-Host "  Installing root dependencies..." -ForegroundColor Gray
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install root dependencies" -ForegroundColor Red
    exit 1
}

# API dependencies
Write-Host "  Installing API dependencies..." -ForegroundColor Gray
Push-Location services\api
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install API dependencies" -ForegroundColor Red
    exit 1
}
Pop-Location

Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Step 2: Setup environment
Write-Host "Step 2: Setting up environment..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env file from template" -ForegroundColor Green
    Write-Host "⚠️  Please edit .env with your settings" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env already exists" -ForegroundColor Green
}

Write-Host ""

# Step 3: Database setup
Write-Host "Step 3: Database setup" -ForegroundColor Yellow
Write-Host ""

$dbSetup = Read-Host "Do you want to setup the local database now? (y/n)"
if ($dbSetup -eq "y") {
    $dbUrl = Read-Host "Enter PostgreSQL connection string (e.g., postgresql://postgres:password@localhost:5432/nexa_core_dev)"
    
    Write-Host "  Creating database schema..." -ForegroundColor Gray
    psql $dbUrl -f db\schema.sql
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database schema created" -ForegroundColor Green
    } else {
        Write-Host "❌ Database setup failed. You can run manually: psql `$DATABASE_URL < db\schema.sql" -ForegroundColor Red
    }
} else {
    Write-Host "⏭️  Skipping database setup" -ForegroundColor Yellow
    Write-Host "   Run manually: psql `$DATABASE_URL < db\schema.sql" -ForegroundColor Gray
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Edit .env with your database URL and secrets" -ForegroundColor White
Write-Host "2. Start the API server:" -ForegroundColor White
Write-Host "   cd services\api" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test the API:" -ForegroundColor White
Write-Host "   curl http://localhost:3000/health" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Deploy Multi-Spec Analyzer (if not done):" -ForegroundColor White
Write-Host "   Go to Render Dashboard → nexa-doc-analyzer-oct2025 → Manual Deploy" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Upload 50 spec PDFs:" -ForegroundColor White
Write-Host "   python ..\backend\pdf-service\batch_upload_50_specs.py C:\path\to\specs\" -ForegroundColor Gray
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "   - README.md - Architecture overview" -ForegroundColor Gray
Write-Host "   - GETTING_STARTED.md - Detailed setup guide" -ForegroundColor Gray
Write-Host "   - DEPLOYMENT_PLAN.md - Production deployment" -ForegroundColor Gray
Write-Host ""
Write-Host "🎉 Happy coding!" -ForegroundColor Green
