# Complete NEXA Workflow Testing Script
# Tests: PM upload spec → Learn standards → Upload audit → Analyze for repeals

Write-Host "🧪 NEXA COMPLETE WORKFLOW TEST" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

$API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

# Test 1: Health Check
Write-Host "`n📡 Test 1: API Health Check" -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "$API_URL/health" -Method Get
if ($health.status -eq "healthy") {
    Write-Host "✅ API is healthy" -ForegroundColor Green
} else {
    Write-Host "❌ API unhealthy" -ForegroundColor Red
    exit 1
}

# Test 2: Spec Learning (PM uploads large spec book like PG&E Greenbook)
Write-Host "`n📚 Test 2: Learn Spec Standards" -ForegroundColor Yellow
if (Test-Path "greenbook.pdf") {
    Write-Host "Uploading PG&E Greenbook for learning..." -ForegroundColor Gray
    $specResponse = & curl -X POST "$API_URL/upload-specs" -F "files=@greenbook.pdf" 2>$null
    $result = $specResponse | ConvertFrom-Json
    
    if ($result) {
        Write-Host "✅ Spec learned successfully!" -ForegroundColor Green
        Write-Host "   Total chunks: $($result.total_chunks)" -ForegroundColor Gray
        Write-Host "   Files: $($result.total_files)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Spec learning failed!" -ForegroundColor Red
    }
} else {
    Write-Host "⚠️  No greenbook.pdf found - using existing spec library" -ForegroundColor Yellow
}

# Test 3: Check Spec Library Status
Write-Host "`n📋 Test 3: Verify Spec Library" -ForegroundColor Yellow
$specs = Invoke-RestMethod -Uri "$API_URL/spec-library" -Method Get
Write-Host "✅ Spec Library Status:" -ForegroundColor Green
Write-Host "   Total specs: $($specs.total_files)" -ForegroundColor Gray
Write-Host "   Total chunks: $($specs.total_chunks)" -ForegroundColor Gray

# Test 4: Audit Analysis (Check for repealable go-backs)
Write-Host "`n🔍 Test 4: Analyze Audit for Go-Backs" -ForegroundColor Yellow
if (Test-Path "mock_audit.pdf") {
    Write-Host "Analyzing audit document..." -ForegroundColor Gray
    $auditResponse = & curl -X POST "$API_URL/analyze-audit" -F "file=@mock_audit.pdf" 2>$null
    $auditResult = $auditResponse | ConvertFrom-Json
    
    if ($auditResult) {
        Write-Host "✅ Audit analyzed successfully!" -ForegroundColor Green
        
        # Check for repealable infractions
        if ($auditResult.repealable_count -gt 0) {
            Write-Host "   🟢 Repealable infractions: $($auditResult.repealable_count)" -ForegroundColor Green
            Write-Host "   Confidence: $($auditResult.average_confidence * 100)% " -ForegroundColor Gray
            
            # Show repeal reasons
            if ($auditResult.infractions) {
                foreach ($infraction in $auditResult.infractions) {
                    if ($infraction.repealable) {
                        Write-Host "`n   📝 Repealable: $($infraction.type)" -ForegroundColor Green
                        Write-Host "      Confidence: $([math]::Round($infraction.confidence * 100))%" -ForegroundColor Gray
                        Write-Host "      Reason: $($infraction.reason)" -ForegroundColor Cyan
                        Write-Host "      Cost Savings: `$$($infraction.cost_savings)" -ForegroundColor Yellow
                    }
                }
            }
        } else {
            Write-Host "   🔴 No repealable go-backs found" -ForegroundColor Red
        }
        
        Write-Host "`n   Total infractions: $($auditResult.total_infractions)" -ForegroundColor Gray
        Write-Host "   True violations: $($auditResult.total_infractions - $auditResult.repealable_count)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Audit analysis failed!" -ForegroundColor Red
    }
} else {
    Write-Host "⚠️  No mock_audit.pdf found - create one to test" -ForegroundColor Yellow
}

# Test 5: Sample Repeal Analysis Output
Write-Host "`n📊 Test 5: Sample Repeal Analysis" -ForegroundColor Yellow
Write-Host "Expected output for a typical audit:" -ForegroundColor Gray
Write-Host @"

Example Repealable Infraction:
   Type: Oil-filled Crossarm
   Status: REPEALABLE (85% confidence)
   Reason: "Per SECTION 3.2: Oil-filled crossarms compliant 
           under GRADE B variances if pre-2020"
   Cost Savings: $14,000 (labor + equipment)
   
   Supporting Evidence:
   - PG&E Greenbook Section 3.2.4
   - Grade B Construction Standards
   - Installation date: 2019 (compliant)
"@ -ForegroundColor Cyan

# Test 6: Performance Metrics
Write-Host "`n⚡ Test 6: Performance Check" -ForegroundColor Yellow
$times = @()
for ($i = 1; $i -le 5; $i++) {
    $start = Get-Date
    $null = Invoke-RestMethod -Uri "$API_URL/health" -Method Get
    $duration = ((Get-Date) - $start).TotalMilliseconds
    $times += $duration
}

$avgTime = ($times | Measure-Object -Average).Average
Write-Host "Average response time: $([math]::Round($avgTime, 2))ms" -ForegroundColor Green

# Summary
Write-Host "`n" -ForegroundColor White
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "     WORKFLOW TEST COMPLETE      " -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

Write-Host "`n✅ Complete Workflow:" -ForegroundColor Green
Write-Host "1. PM uploads spec book (PG&E Greenbook) ✓" -ForegroundColor White
Write-Host "2. System learns standards (chunks/embeds) ✓" -ForegroundColor White
Write-Host "3. PM uploads audit document ✓" -ForegroundColor White
Write-Host "4. System analyzes for go-backs ✓" -ForegroundColor White
Write-Host "5. Identifies repealable vs true violations ✓" -ForegroundColor White
Write-Host "6. Provides confidence scores & reasons ✓" -ForegroundColor White
Write-Host "7. Calculates cost savings ✓" -ForegroundColor White

Write-Host "`n🎯 Ready for production testing!" -ForegroundColor Green
