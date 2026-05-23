@echo off
setlocal
set "BOTTY_DIR=%~dp0"
cd /d "%BOTTY_DIR%"

call "%BOTTY_DIR%find_python.bat"

%PYTHON% "%BOTTY_DIR%quest_debug.py"
