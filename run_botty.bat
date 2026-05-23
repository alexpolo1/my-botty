@echo off
setlocal
set "BOTTY_DIR=%~dp0"
cd /d "%BOTTY_DIR%"

call "%BOTTY_DIR%find_python.bat"

echo Launching Botty ...
%PYTHON% "%BOTTY_DIR%src\main.py"
pause
