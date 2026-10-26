@echo off
TITLE Friday Music Bot
:: Checking for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

echo [INFO] Starting Friday Music Bot...
python -m SANYAMUSIC
pause
