# Test PDF analysis with a small test file
$baseUrl = "https://nexa-doc-analyzer-oct2025.onrender.com"

Write-Host "`n🧪 Testing PDF Analysis..." -ForegroundColor Cyan

# Create a minimal test PDF content (this is a valid PDF structure)
$pdfContent = @"
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF: TAG-2 pole replacement) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
344
%%EOF
"@

# Save as test PDF
$testPdf = "test_analyze.pdf"
[System.IO.File]::WriteAllBytes($testPdf, [System.Text.Encoding]::UTF8.GetBytes($pdfContent))

Write-Host "📄 Created test PDF: $testPdf" -ForegroundColor Green

# Test with curl first (more reliable for file uploads)
Write-Host "`n📤 Uploading via curl..." -ForegroundColor Yellow

$result = curl -X POST "$baseUrl/analyze-audit" `
  -F "job_package=@$testPdf" `
  -H "Accept: application/json" `
  --silent `
  --show-error

Write-Host "`n📊 Response:" -ForegroundColor Cyan
$result | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Clean up
Remove-Item $testPdf -ErrorAction SilentlyContinue

Write-Host "`n✅ Test complete!" -ForegroundColor Green
