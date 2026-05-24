@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo  Botty - Updater
echo ============================================
echo.

:: --- Check git is available ---
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: git is not installed or not in PATH.
    echo Download from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

:: --- Pull latest changes ---
echo Pulling latest changes from GitHub...
echo.
git pull
if %errorlevel% neq 0 (
    echo.
    echo ERROR: git pull failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Update complete! Re-run install.bat if
echo  environment.yml changed, then run_botty.bat
echo ============================================
echo.
pause
