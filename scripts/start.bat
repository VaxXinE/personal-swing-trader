@echo off
setlocal
cd /d "%~dp0.."
REM Do not perform network package installation during server startup.
if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Create it: py -3 -m venv .venv
    echo Then install manually: .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    exit /b 1
)
.venv\Scripts\python.exe -c "import fastapi,uvicorn,httpx,pydantic" >nul 2>&1
if errorlevel 1 (
    echo Backend packages missing. Explicitly install requirements before startup.
    exit /b 1
)
echo %* | findstr /C:"--live" >nul
if not errorlevel 1 (
    .venv\Scripts\python.exe -c "import yfinance" >nul 2>&1
    if errorlevel 1 (
        echo LIVE extras missing. Run: .venv\Scripts\python.exe -m pip install -r backend\requirements-live.txt
        exit /b 1
    )
)
.venv\Scripts\python.exe scripts\launch.py %*
exit /b %errorlevel%
