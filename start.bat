@echo off
REM ============================================================
REM  BookSmart — Windows launcher
REM  Double-click karo ya terminal me: start.bat
REM ============================================================
cd /d %~dp0

if not exist .venv (
    echo [1/3] Creating Python environment...
    python -m venv .venv
)

echo [2/3] Activating environment...
call .venv\Scripts\activate.bat

echo [3/3] Installing dependencies (first time only)...
pip install -r requirements.txt >nul 2>&1

echo.
echo  -------------------------------------------------
echo   BookSmart starting...  http://localhost:8000
echo  -------------------------------------------------
echo.
python run.py
pause
