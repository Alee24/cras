@echo off
title CRAS - Compliance Risk Analytics System
echo ============================================================
echo   COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)
echo   Regulatory Compliance and Risk Intelligence for SMEs in Kenya
echo ============================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Creating virtual environment and installing dependencies...
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
)

echo Starting CRAS local server on http://localhost:5000 ...
start "" "http://localhost:5000"
.\.venv\Scripts\python wsgi.py
pause
