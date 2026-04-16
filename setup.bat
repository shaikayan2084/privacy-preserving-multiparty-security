@echo off
title SMPC Shield — Setup

echo.
echo  =========================================================
echo   SMPC Shield - Privacy-Preserving Data Collaboration
echo   VVIT Nambur - B.Tech Final Year Project 2025-2026
echo  =========================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause & exit /b 1
)
echo  [OK] Python found

:: Create virtual environment
if not exist venv (
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
    echo  [OK] Virtual environment created
) else (
    echo  [OK] Virtual environment exists
)

:: Activate and install deps
echo  [SETUP] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

:: Copy .env if not exists
if not exist .env (
    echo  [SETUP] Creating .env from example...
    copy .env.example .env >nul
    echo  [!] Edit .env with your email credentials
)

:: Create dirs
if not exist logs mkdir logs
if not exist instance mkdir instance

echo.
echo  =========================================================
echo   Setup complete!
echo.
echo   To run the app:
echo     1. venv\Scripts\activate
echo     2. python run.py
echo   OR: double-click run.bat
echo.
echo   Open in VS Code:
echo     code smpc-shield.code-workspace
echo  =========================================================
echo.
pause
