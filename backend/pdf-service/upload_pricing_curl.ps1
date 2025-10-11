# Upload Pricing Master CSV to NEXA Backend using curl
# This builds the searchable FAISS index for pricing lookups

$baseUrl = "https://nexa-doc-analyzer-oct2025.onrender.com"

Write-Host "🚀 Uploading PG&E Pricing Master to NEXA Backend..." -ForegroundColor Cyan

# Check if pricing master CSV exists
$pricingFile = "pge_prices_master_stockton_filled_TAG_only.csv"
if (-not (Test-Path $pricingFile)) {
    Write-Host "❌ Error: $pricingFile not found in current directory" -ForegroundColor Red
    exit 1
}

# Check if curl is available
if (-not (Get-Command curl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: curl is not installed" -ForegroundColor Red
    exit 1
}

# Upload the pricing master using curl
Write-Host "📤 Uploading $pricingFile..." -ForegroundColor Yellow

$curlCommand = @"
curl -X POST "$baseUrl/pricing/learn-pricing" `
  -F "pricing_file=@$pricingFile" `
  -F "region=Stockton"
"@

Write-Host "Executing: $curlCommand" -ForegroundColor Gray

# Execute curl
$result = Invoke-Expression $curlCommand

# Parse result
try {
    $response = $result | ConvertFrom-Json
    if ($response.status -eq "success") {
        Write-Host "✅ Pricing data uploaded successfully!" -ForegroundColor Green
        if ($response.details) {
            Write-Host "   - Total entries: $($response.details.entries_indexed)" -ForegroundColor White
            Write-Host "   - Programs: $($response.details.programs -join ', ')" -ForegroundColor White
        }
    } else {
        Write-Host "⚠️ Unexpected response: $result" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Response: $result" -ForegroundColor Yellow
}

# Check pricing status
Write-Host "`n📊 Checking pricing status..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

try {
    $status = Invoke-RestMethod -Uri "$baseUrl/pricing/pricing-status"
    
    Write-Host "`n🎯 Pricing System Status:" -ForegroundColor Green
    Write-Host "   - Status: $($status.status)" -ForegroundColor White
    
    if ($status.total_entries) {
        Write-Host "   - Total entries: $($status.total_entries)" -ForegroundColor White
    }
    if ($status.labor_rates) {
        Write-Host "   - Labor rates: $($status.labor_rates)" -ForegroundColor White
    }
    if ($status.equipment_rates) {
        Write-Host "   - Equipment rates: $($status.equipment_rates)" -ForegroundColor White
    }
    
    if ($status.programs) {
        Write-Host "   - Programs loaded:" -ForegroundColor White
        foreach ($prog in $status.programs.PSObject.Properties) {
            Write-Host "     • $($prog.Name): $($prog.Value.count) items" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "⚠️ Could not check status: $_" -ForegroundColor Yellow
}

Write-Host "`n✨ Pricing system ready for cost calculations!" -ForegroundColor Green
