@echo off
REM ============================================================
REM  BookSmart LLM Starter (Windows) — one click me AI on!
REM
REM  BAS YEH 2 PATHS EDIT KARO (apne PC ke hisaab se):
REM  1. LLAMAFILE_EXE -> aapke llamafile-0.10.5 folder me llamafile.exe
REM  2. MODEL_FILE    -> aapke qwen3-4b gguf file ka full path
REM
REM  Phir is file ko double-click karo. Bas! ✅
REM ============================================================

set LLAMAFILE_EXE=C:\path\to\llamafile-0.10.5\llamafile.exe
set MODEL_FILE=C:\path\to\qwen3-4b-thinking-2507.Q4_K_M.gguf
set PORT=8080

echo.
echo  ------------------------------------------------
echo   BookSmart AI starting on http://localhost:%PORT%
echo   (is window ko BAND mat karna — AI yahi chalta hai)
echo  ------------------------------------------------
echo.

"%LLAMAFILE_EXE%" -m "%MODEL_FILE%" --server --host 0.0.0.0 --port %PORT% --jinja --ctx-size 8192

echo.
echo AI server band ho gaya. Window band kar sakte ho.
pause
