@echo off
title AgroAI
cd /d "%~dp0"

echo ========================================
echo             AgroAI
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please create .venv and install requirements first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Please create .env from .env.example and add your keys.
    pause
    exit /b 1
)

echo Starting AgroAI...
echo.

".venv\Scripts\python.exe" main.py

echo.
echo AgroAI stopped.
pause