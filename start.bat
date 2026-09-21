@echo off
title AgroAI
cd /d "%~dp0"

echo ========================================
echo              AgroAI
echo ========================================
echo.

echo [1/4] Checking Python...

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed.
    echo Please install Python 3.13 or newer and try again.
    echo.
    pause
    exit /b 1
)

python --version
echo.

echo [2/4] Checking virtual environment...

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Creating .venv...
    echo.

    python -m venv .venv

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )

    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo [3/4] Installing required libraries...
echo.

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install required libraries.
    echo Check your Internet connection and requirements.txt.
    echo.
    pause
    exit /b 1
)

echo.
echo Libraries installed successfully.
echo.

echo [4/4] Checking configuration...

if not exist ".env" (
    echo.
    echo [ERROR] .env file not found.
    echo.
    echo Please create .env in the project folder.
    echo Required variables:
    echo BOT_TOKEN
    echo COPERNICUS_CLIENT_ID
    echo COPERNICUS_CLIENT_SECRET
    echo.
    pause
    exit /b 1
)

echo Configuration file found.
echo.

echo ========================================
echo             Starting AgroAI
echo ========================================
echo.

".venv\Scripts\python.exe" main.py

echo.
echo ========================================
echo             AgroAI stopped
echo ========================================
echo.
pause