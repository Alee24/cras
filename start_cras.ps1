# CRAS - Compliance Risk Analytics System
# PowerShell Startup and Management Script

param(
    [switch]$Migrate,
    [switch]$Seed,
    [string]$Db = "",
    [int]$Port = 5000,
    [switch]$NoBrowser
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)" -ForegroundColor Yellow
Write-Host "  Regulatory Compliance and Risk Intelligence for SMEs in Kenya" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot

$pythonCmd = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonCmd = ".\.venv\Scripts\python.exe"
} else {
    Write-Host "[CRAS] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    if (Test-Path ".\.venv\Scripts\python.exe") {
        & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
        & ".\.venv\Scripts\pip.exe" install -r requirements.txt
        $pythonCmd = ".\.venv\Scripts\python.exe"
    } else {
        Write-Host "[CRAS] Using system Python..." -ForegroundColor Yellow
        $pythonCmd = "python"
    }
}

$cliArgs = @()
if ($Migrate) { $cliArgs += "--migrate" }
if ($Seed) { $cliArgs += "--seed" }
if ($Db) { $cliArgs += @("--db", $Db) }
if ($Port -ne 5000) { $cliArgs += @("--port", $Port.ToString()) }
if ($NoBrowser) { $cliArgs += "--no-browser" }

& $pythonCmd run.py @cliArgs $args
