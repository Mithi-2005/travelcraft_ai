@echo off
setlocal

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Virtual environment Python not found at:
    echo %VENV_PYTHON%
    echo.
    echo Create the virtual environment and install dependencies first.
    exit /b 1
)

"%VENV_PYTHON%" -m uvicorn app.main:app --reload --port 8000
