@echo off
title SMPC Shield - Running

echo.
echo  [SMPC] Starting Privacy-Preserving Data Collaboration App...
echo  [SMPC] URL: http://127.0.0.1:5000
echo  [SMPC] Press Ctrl+C to stop
echo.

call venv\Scripts\activate.bat 2>nul || (
    echo  [!] venv not found. Run setup.bat first.
    pause & exit /b 1
)

python run.py
pause
