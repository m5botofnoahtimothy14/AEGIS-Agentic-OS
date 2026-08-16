@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo    SATURDAY AI OS - Unified Boot
echo ============================================
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment at "%cd%\.venv"
        pause
        exit /b 1
    )
)
set TF_HUB_CACHE_DIR=%CD%\.tensorflow\hub
set HF_HOME=%CD%\.huggingface
set TORCH_HOME=%CD%\.torch
set DEEPFACE_HOME=%CD%\.deepface
set KERAS_HOME=%CD%\.keras
set TF_CPP_MIN_LOG_LEVEL=2
echo.
echo Preflight + device optimization + core boot...
".venv\Scripts\python.exe" saturday_boot.py --watch
echo.
echo SATURDAY stopped. Press any key to close.
pause >nul
