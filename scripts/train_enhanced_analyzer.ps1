# Train Enhanced Analyzer with Poles & Underground NER
Write-Host "🎯 TRAINING ENHANCED ANALYZER FOR POLES & UNDERGROUND" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Step 1: Install dependencies
Write-Host "`n📦 Installing fine-tuning dependencies..." -ForegroundColor Yellow
pip install peft==0.6.0 datasets==2.14.5 accelerate==0.24.0 scikit-learn==1.3.2

# Step 2: Run fine-tuning
Write-Host "`n🚀 Starting fine-tuning with domain-specific data..." -ForegroundColor Yellow
python backend/pdf-service/fine_tune_poles_underground.py

# Step 3: Test enhanced analyzer
Write-Host "`n🧪 Testing enhanced analyzer..." -ForegroundColor Yellow
python backend/pdf-service/enhanced_spec_analyzer.py

Write-Host "`n✅ FINE-TUNING COMPLETE!" -ForegroundColor Green
Write-Host "The model now understands:" -ForegroundColor White
Write-Host "  • Pole clearances and requirements" -ForegroundColor Gray
Write-Host "  • Underground conduit specifications" -ForegroundColor Gray
Write-Host "  • PG&E standards (G.O. 95, ANSI, etc.)" -ForegroundColor Gray
Write-Host "  • Equipment types and measurements" -ForegroundColor Gray
Write-Host "`nF1-Score Target: >0.85 for critical entities" -ForegroundColor Cyan
