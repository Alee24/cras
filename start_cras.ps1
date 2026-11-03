Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)" -ForegroundColor Yellow
Write-Host "  Regulatory Compliance and Risk Intelligence for SMEs in Kenya" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment and installing packages..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

Write-Host "Opening web browser at http://localhost:5000..." -ForegroundColor Green
Start-Process "http://localhost:5000"

Write-Host "Starting CRAS web application..." -ForegroundColor Cyan
.\.venv\Scripts\python wsgi.py

