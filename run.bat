@echo off
TITLE Intelligent Data Analysis Assistant (IDAA)
COLOR 0B

echo ============================================================
echo   INTELLIGENT DATA ANALYSIS ASSISTANT (IDAA)
echo   Data Science Mini Project - Setup ^& Launch Script
echo ============================================================
echo.

python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python was not found on your system.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

IF NOT EXIST "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
) ELSE (
    echo [1/4] Virtual environment already exists, skipping...
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing required packages ^(this may take a minute on first run^)...
pip install --upgrade pip >nul
pip install -r requirements.txt

echo [4/4] Launching IDAA server...
echo.
echo ------------------------------------------------------------
echo   Open your browser at:  http://127.0.0.1:5000
echo   Press CTRL+C in this window to stop the server.
echo ------------------------------------------------------------
echo.

python app.py

pause
