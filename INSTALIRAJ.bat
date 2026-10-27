@echo off
rem WhisperWriter - instalacija jednim klikom / one-click install (Windows 10/11).
rem Instalira uv (on sam skida Python 3.11), biblioteke, srpska podesavanja i precicu.
title WhisperWriter - instalacija / install
cd /d "%~dp0"
echo.
echo ===== WhisperWriter - instalacija / install =====
echo.

rem --- 1. uv (upravlja Python-om i bibliotekama) ---
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if defined UV goto have_uv

echo [1/3] Instaliram uv / Installing uv ...
winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if defined UV goto have_uv
echo.
echo GRESKA / ERROR: uv nije instaliran / uv is not installed. Zatvori prozor i pokreni INSTALIRAJ.bat ponovo / Close this window and run INSTALIRAJ.bat again.
echo Rucno / Manual install: https://docs.astral.sh/uv/
pause
exit /b 1

:have_uv
rem --- 2. Python 3.11 + biblioteke ---
echo [2/3] Python + biblioteke / libraries (par minuta / a few minutes) ...
if not exist ".venv\Scripts\python.exe" (
    "%UV%" venv --python 3.11 .venv
    if errorlevel 1 goto failed
)
"%UV%" pip install --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 goto failed

rem --- 3. Podesavanja, model, precica, kljucevi (pitanja na srpskom) ---
echo [3/3] Podesavanja / Settings ...
".venv\Scripts\python.exe" src\setup_wizard.py install
if errorlevel 1 goto failed
echo.
pause
exit /b 0

:failed
echo.
echo GRESKA / ERROR. Proveri internet i pokreni INSTALIRAJ.bat ponovo / Check your internet and run INSTALIRAJ.bat again.
pause
exit /b 1
