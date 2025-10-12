# Quick test script for fixed endpoints
Write-Host "🧪 Testing Fixed Universal Standards Endpoints" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host ""

# Wait for deployment to complete (optional)
$waitForDeploy = Read-Host "Wait for Render deployment to complete? (y/n)"
if ($waitForDeploy -eq 'y') {
    Write-Host "⏳ Waiting for Render to rebuild (typically 5-10 minutes)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 300  # 5 minutes
}

$baseUrl = "https://nexa-us-pro.onrender.com"

# Test 1: Authentication
Write-Host "🔐 Testing Authentication..." -ForegroundColor Yellow
try {
    $body = @{
        email = "admin@nexa.com"
        password = "admin123"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    $token = $response.access_token
    Write-Host "   ✅ Login successful! Token received" -ForegroundColor Green
    Write-Host "   User: $($response.user.email) - Role: $($response.user.role)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Authentication failed: $_" -ForegroundColor Red
    $token = $null
}

Write-Host ""

# Test 2: List Utilities (no auth required now)
Write-Host "📋 Testing List Utilities..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/utilities/list" -Method GET
    Write-Host "   ✅ Found $($response.total) utilities" -ForegroundColor Green
    foreach ($util in $response.utilities) {
        Write-Host "      - $($util.name) ($($util.id))" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: GPS Detection
Write-Host "🗺️ Testing GPS Detection (San Francisco)..." -ForegroundColor Yellow
try {
    $body = @{
        lat = 37.7749
        lng = -122.4194
    } | ConvertTo-Json
    
    $headers = @{"Content-Type" = "application/json"}
    if ($token) {
        $headers["Authorization"] = "Bearer $token"
    }
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/utilities/detect" `
        -Method POST `
        -Headers $headers `
        -Body $body
    
    Write-Host "   ✅ Detected: $($response.utility_id)" -ForegroundColor Green
    if ($response.utility_info) {
        Write-Host "      Utility: $($response.utility_info.name)" -ForegroundColor Gray
        Write-Host "      Region: $($response.utility_info.region)" -ForegroundColor Gray
    }
    if ($response.user) {
        Write-Host "      User: $($response.user)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 4: Cross-Reference
Write-Host "🔄 Testing Cross-Reference..." -ForegroundColor Yellow
try {
    $body = @{
        requirement = "capacitor spacing"
    } | ConvertTo-Json
    
    $headers = @{"Content-Type" = "application/json"}
    if ($token) {
        $headers["Authorization"] = "Bearer $token"
    }
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/utilities/standards/cross-reference" `
        -Method POST `
        -Headers $headers `
        -Body $body
    
    Write-Host "   ✅ Cross-referenced across $($response.utilities_compared) utilities" -ForegroundColor Green
    foreach ($utilId in $response.cross_references.PSObject.Properties.Name) {
        $ref = $response.cross_references.$utilId
        Write-Host "      - $($ref.utility_name): $($ref.matching_sections -join ', ')" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 5: Audit Analysis (should have default spec now)
Write-Host "🔍 Testing Audit Analysis Readiness..." -ForegroundColor Yellow
try {
    # Just check if spec library is initialized
    $response = Invoke-RestMethod -Uri "$baseUrl/spec-library" -Method GET
    if ($response.total_chunks -gt 0) {
        Write-Host "   ✅ Spec library initialized with $($response.total_chunks) chunks" -ForegroundColor Green
        Write-Host "      Files: $($response.total_files)" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️ Spec library empty (will initialize on first audit analysis)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "   If all tests pass, Universal Standards Engine is fully operational!" -ForegroundColor Green
Write-Host "   Run full test suite: python tests\test_universal.py prod" -ForegroundColor Yellow
