@echo off
rem Unos API kljuceva / API key setup (ElevenLabs, Groq).
title WhisperWriter - API kljucevi / API keys
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Prvo pokreni / First run: INSTALIRAJ.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" src\setup_wizard.py keys
echo.
pause
