@echo off
setlocal
set "BOTTY_DIR=%~dp0"
cd /d "%BOTTY_DIR%"

call "%BOTTY_DIR%find_python.bat"

echo === D2R Quick Capture ===
echo Run this, D2R must be visible
echo Press ENTER when D2R is ready...
pause >nul

%PYTHON% "%BOTTY_DIR%asset_extractor.py"
