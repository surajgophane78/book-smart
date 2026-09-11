@echo off
setlocal
cd /d "%~dp0"
title BookSmart Master Launcher

REM ======================================================
REM  BookSmart - ONE-CLICK START (App + Local AI together)
REM
REM  ONE-TIME SETUP:
REM   1. Right-click this file -> Edit (or open in VS Code)
REM   2. Fix the 2 paths below (where YOUR llamafile + model are)
REM   3. Save. From now on, just double-click this file.
REM ======================================================
set "LLAMAFILE_EXE=C:\path\to\llamafile-0.10.5\llamafile.exe"
set "MODEL_FILE=C:\path\to\qwen3-4b-thinking-2507.Q4_K_M.gguf"
set "LLM_PORT=8080"
set "APP_PORT=8000"

echo.
echo  ================================================
echo    BookSmart  -  starting everything for you...
echo  ================================================
echo.

REM ---------- 0) Did you set your paths? ----------
echo "%LLAMAFILE_EXE%" | find /i "path\to" >nul
if not errorlevel 1 goto need_edit
goto check_ai_files

:need_edit
echo  [SETUP] You have not set your paths yet!
echo.
echo    1. Right-click START-BOOKSMART.bat -^> Edit
echo    2. Change these two lines at the top:
echo         set "LLAMAFILE_EXE=..."
echo         set "MODEL_FILE=..."
echo    3. Save, then double-click again.
echo.
pause
exit /b 1

REM ---------- 1) LOCAL AI (llamafile + Qwen3) ----------
:check_ai_files
if not exist "%LLAMAFILE_EXE%" goto no_llamafile
if not exist "%MODEL_FILE%" goto no_model

curl -s -o nul -m 2 "http://127.0.0.1:%LLM_PORT%/v1/models"
if not errorlevel 1 goto llm_reuse

echo  [AI] Starting llamafile (Qwen3-4B)...
echo  [AI] First load takes 1-3 minutes - please wait.
start "BookSmart-AI" "%LLAMAFILE_EXE%" -m "%MODEL_FILE%" --server --host 127.0.0.1 --port %LLM_PORT% --jinja --ctx-size 8192
echo  [AI] Waiting for the model to load
set TRIES=0

:wait_llm
curl -s -o nul -m 2 "http://127.0.0.1:%LLM_PORT%/v1/models"
if not errorlevel 1 goto llm_ready
set /a TRIES+=1
if %TRIES% GEQ 90 goto llm_slow
<nul set /p "=."
timeout /t 2 /nobreak >nul
goto wait_llm

:llm_reuse
echo  [AI] Already running on port %LLM_PORT% - reusing it [OK]
goto llm_done

:llm_ready
echo.
echo  [AI] Ready [OK] - Qwen3 is live on port %LLM_PORT%
goto llm_done

:llm_slow
echo.
echo  [AI] Model is taking too long - check the "BookSmart-AI" window.
echo  [AI] Continuing anyway (AI may come online later)...
goto llm_done

:no_llamafile
echo  [AI] llamafile.exe NOT found:
echo        %LLAMAFILE_EXE%
echo  [AI] Fix the path at the top of this file.
echo  [AI] Continuing WITHOUT AI (reading / TTS / notes still work)...
goto llm_done

:no_model
echo  [AI] Model file NOT found:
echo        %MODEL_FILE%
echo  [AI] Fix the path at the top of this file.
echo  [AI] Continuing WITHOUT AI (reading / TTS / notes still work)...

:llm_done
echo.

REM ---------- 2) PYTHON ENV (first run auto-setup) ----------
if exist ".venv\Scripts\python.exe" goto venv_ok

echo  [APP] First run - creating Python environment (one time, 1-2 min)...
python -m venv .venv
if errorlevel 1 goto python_missing
.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
goto venv_ok

:python_missing
echo  [ERROR] Python not found! Install Python 3.10+ and tick "Add to PATH".
pause
exit /b 1

:venv_ok
echo  [APP] Python environment ready [OK]
echo.

REM ---------- 3) START THE APP (its own window) ----------
start "BookSmart-App" ".venv\Scripts\python.exe" run.py
echo  [APP] BookSmart is starting on http://localhost:%APP_PORT%
set WTRIES=0

:wait_app
curl -s -o nul -m 1 "http://127.0.0.1:%APP_PORT%/api/health"
if not errorlevel 1 goto app_ready
set /a WTRIES+=1
if %WTRIES% GEQ 40 goto app_ready
timeout /t 1 /nobreak >nul
goto wait_app

:app_ready
echo  [APP] Opening your browser...
start "" "http://localhost:%APP_PORT%"

echo.
echo  ================================================
echo    [DONE] EVERYTHING IS RUNNING!
echo.
echo    App window  : "BookSmart-App"  (keep it open)
echo    AI window   : "BookSmart-AI"   (keep it open)
echo    Browser     : http://localhost:%APP_PORT%
echo.
echo    To STOP everything: double-click STOP-BOOKSMART.bat
echo  ================================================
echo.
pause
endlocal
