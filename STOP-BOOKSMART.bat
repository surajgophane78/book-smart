@echo off
title BookSmart Stop
echo.
echo  Stopping BookSmart...
echo.

REM App window (started with this exact title by START-BOOKSMART.bat)
taskkill /F /T /FI "WINDOWTITLE eq BookSmart-App" >nul 2>&1
if not errorlevel 1 echo  [OK] App stopped

REM AI window + llamafile process (belt and suspenders)
taskkill /F /T /FI "WINDOWTITLE eq BookSmart-AI" >nul 2>&1
if not errorlevel 1 echo  [OK] AI window closed
taskkill /F /IM llamafile.exe >nul 2>&1
if not errorlevel 1 echo  [OK] llamafile stopped

echo.
echo  Done - everything stopped. Bye!
timeout /t 3 >nul
