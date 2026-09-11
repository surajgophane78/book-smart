#!/bin/bash
# BookSmart — Mac/Linux launcher
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "[1/3] Creating Python environment..."
  python3 -m venv .venv
fi

echo "[2/3] Activating environment..."
source .venv/bin/activate

echo "[3/3] Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "  ------------------------------------------------"
echo "   BookSmart starting...  http://localhost:8000"
echo "  ------------------------------------------------"
echo ""
python run.py
