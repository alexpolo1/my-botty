@echo off
setlocal

set "BOTTY_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%BOTTY_DIR%tools\check_dependencies.ps1"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo Dependency check reported issues.
)

pause
exit /b %RC%

