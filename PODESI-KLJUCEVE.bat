@echo off
rem Unos API kljuceva (ElevenLabs, Groq) za brzo prepoznavanje preko interneta.
title WhisperWriter - API kljucevi
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Prvo pokreni INSTALIRAJ.bat.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" src\setup_wizard.py keys
echo.
pause
