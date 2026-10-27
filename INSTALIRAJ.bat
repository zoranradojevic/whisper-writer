@echo off
rem WhisperWriter - instalacija jednim klikom (Windows 10/11).
rem Instalira uv (on sam skida Python 3.11), biblioteke, srpska podesavanja i precicu.
title WhisperWriter - instalacija
cd /d "%~dp0"
echo.
echo ===== WhisperWriter - instalacija =====
echo.

rem --- 1. uv (upravlja Python-om i bibliotekama) ---
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if defined UV goto have_uv

echo [1/3] Instaliram uv ...
winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if defined UV goto have_uv
echo.
echo GRESKA: uv nije instaliran. Zatvori ovaj prozor, pa ponovo pokreni INSTALIRAJ.bat.
echo Ako opet ne radi, instaliraj rucno: https://docs.astral.sh/uv/
pause
exit /b 1

:have_uv
rem --- 2. Python 3.11 + biblioteke ---
echo [2/3] Pravim Python okruzenje i instaliram biblioteke (par minuta) ...
if not exist ".venv\Scripts\python.exe" (
    "%UV%" venv --python 3.11 .venv
    if errorlevel 1 goto failed
)
"%UV%" pip install --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 goto failed

rem --- 3. Podesavanja, model, precica, kljucevi (pitanja na srpskom) ---
echo [3/3] Podesavanja ...
".venv\Scripts\python.exe" src\setup_wizard.py install
if errorlevel 1 goto failed
echo.
pause
exit /b 0

:failed
echo.
echo GRESKA tokom instalacije. Proveri internet konekciju i pokreni INSTALIRAJ.bat ponovo.
pause
exit /b 1
