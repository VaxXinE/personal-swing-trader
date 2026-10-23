@echo off
cd /d "%~dp0.."
if not exist .venv (py -3 -m venv .venv)
call .venv\Scripts\activate.bat
echo %* | findstr /C:"--live" >nul
if not errorlevel 1 (
    python -m pip install -r backend\requirements-live.txt
) else (
    python -m pip install -r backend\requirements.txt
)
python scripts\launch.py %*
pause
