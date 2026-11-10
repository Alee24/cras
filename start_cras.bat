@echo off
title CRAS - Compliance Risk Analytics System
echo ============================================================
echo   COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)
echo   Regulatory Compliance and Risk Intelligence for SMEs in Kenya
echo ============================================================
echo.

cd /d "%~dp0"

:: Auto-detect Python or Virtual Environment
set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.\.venv\Scripts\python.exe
) else (
    echo [CRAS] Setting up Python virtual environment...
    python -m venv .venv
    if exist ".venv\Scripts\python.exe" (
        .\.venv\Scripts\python.exe -m pip install --upgrade pip
        .\.venv\Scripts\pip install -r requirements.txt
        set PYTHON_CMD=.\.venv\Scripts\python.exe
    ) else (
        echo [WARNING] Could not create virtual environment. Falling back to system python.
        set PYTHON_CMD=python
    )
)

:: Run CRAS Unified Runner (forwarding any CLI arguments)
%PYTHON_CMD% run.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] CRAS terminated with an error code.
    pause
)
