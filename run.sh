#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  INTELLIGENT DATA ANALYSIS ASSISTANT (IDAA)"
echo "  Data Science Mini Project - Setup & Launch Script"
echo "============================================================"
echo

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 was not found on your system."
    echo "Please install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/4] Virtual environment already exists, skipping..."
fi

echo "[2/4] Activating virtual environment..."
source venv/bin/activate

echo "[3/4] Installing required packages (this may take a minute on first run)..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

echo "[4/4] Launching IDAA server..."
echo
echo "------------------------------------------------------------"
echo "  Open your browser at:  http://127.0.0.1:5000"
echo "  Press CTRL+C in this terminal to stop the server."
echo "------------------------------------------------------------"
echo

python app.py
