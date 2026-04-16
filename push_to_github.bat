@echo off
title GitHub Push — SMPC Shield

echo.
echo  =========================================================
echo   GitHub Push — privacy-preserving-multiparty-security
echo   Repository: https://github.com/shaikayan2084/
echo              privacy-preserving-multiparty-security
echo  =========================================================
echo.

:: Check git
git --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Git not found. Install from git-scm.com
    pause & exit /b 1
)

:: Safety check — never push .env
if exist .env (
    echo  [SAFE]  .env file found — excluded by .gitignore
    echo  [SAFE]  It will NOT be pushed to GitHub
)

:: Init if needed
if not exist .git (
    echo  [GIT]  Initializing repository...
    git init
    git remote add origin https://github.com/shaikayan2084/privacy-preserving-multiparty-security.git
)

:: Status
echo.
echo  [GIT]  Current status:
git status --short

echo.
set /p MSG=Enter commit message (or press Enter for default): 
if "%MSG%"=="" set MSG=Update: SMPC Shield Flask App with security features

:: Stage all (respects .gitignore — .env, *.db, logs/ are excluded)
git add .

:: Show what's being committed
echo.
echo  [GIT]  Files to be committed:
git diff --cached --name-only

echo.
git commit -m "%MSG%"

:: Push
echo.
echo  [GIT]  Pushing to GitHub...
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo  [!] Push failed. Try:
    echo      git push --force-with-lease origin main
    echo  Or check your GitHub credentials
) else (
    echo.
    echo  =========================================================
    echo   Successfully pushed to GitHub!
    echo   https://github.com/shaikayan2084/
    echo   privacy-preserving-multiparty-security
    echo.
    echo   NOTE: .env was NOT pushed (protected by .gitignore)
    echo  =========================================================
)
echo.
pause
