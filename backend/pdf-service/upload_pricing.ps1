# Upload Pricing Master CSV to NEXA Backend
# This builds the searchable FAISS index for pricing lookups

$baseUrl = "https://nexa-doc-analyzer-oct2025.onrender.com"

Write-Host "🚀 Uploading PG&E Pricing Master to NEXA Backend..." -ForegroundColor Cyan

# Check if pricing master CSV exists
$pricingFile = "pge_prices_master_stockton_filled_TAG_only.csv"
if (-not (Test-Path $pricingFile)) {
    Write-Host "❌ Error: $pricingFile not found in current directory" -ForegroundColor Red
    exit 1
}

# Upload the pricing master
Write-Host "📤 Uploading $pricingFile..." -ForegroundColor Yellow

try {
    # Create multipart form data with file and region
    $boundary = [System.Guid]::NewGuid().ToString()
    $filePath = Get-Item $pricingFile
    $fileBytes = [System.IO.File]::ReadAllBytes($filePath.FullName)
    
    # Build multipart body
    $bodyLines = @(
        "--$boundary",
        'Content-Disposition: form-data; name="pricing_file"; filename="' + $filePath.Name + '"',
        "Content-Type: text/csv",
        "",
        [System.Text.Encoding]::UTF8.GetString($fileBytes),
        "--$boundary",
        'Content-Disposition: form-data; name="region"',
        "",
        "Stockton",
        "--$boundary--"
    )
    
    $body = $bodyLines -join "`r`n"
    
    # Upload to learn-pricing endpoint
    $response = Invoke-RestMethod -Uri "$baseUrl/pricing/learn-pricing" `
        -Method POST `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Body $body `
        -TimeoutSec 60
    
    if ($response.status -eq "success") {
        Write-Host "✅ Pricing data uploaded successfully!" -ForegroundColor Green
        Write-Host "   - Total entries: $($response.total_entries)" -ForegroundColor White
        Write-Host "   - Programs: $($response.programs -join ', ')" -ForegroundColor White
    } else {
        Write-Host "⚠️ Unexpected response: $($response | ConvertTo-Json)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error uploading pricing data: $_" -ForegroundColor Red
    exit 1
}

# Check pricing status
Write-Host "`n📊 Checking pricing status..." -ForegroundColor Cyan
try {
    $status = Invoke-RestMethod -Uri "$baseUrl/pricing/pricing-status"
    
    Write-Host "`n🎯 Pricing System Status:" -ForegroundColor Green
    Write-Host "   - Status: $($status.status)" -ForegroundColor White
    Write-Host "   - Total entries: $($status.total_entries)" -ForegroundColor White
    Write-Host "   - Labor rates: $($status.labor_rates)" -ForegroundColor White
    Write-Host "   - Equipment rates: $($status.equipment_rates)" -ForegroundColor White
    
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
