@echo off
setlocal enabledelayedexpansion

set "BOTTY_DIR=%~dp0"
cd /d "%BOTTY_DIR%"

call "%BOTTY_DIR%find_python.bat"

:: Derive the conda env root from python.exe:
::   envs\botty\python.exe  ->  envs\botty
for %%F in ("%PYTHON%") do set "_ENV=%%~dpF"
set "_ENV=%_ENV:~0,-1%"

:: Match an activated conda environment closely enough for native DLL loading.
set "PATH=%_ENV%;%_ENV%\Library\bin;%_ENV%\Library\mingw-w64\bin;%_ENV%\Library\usr\bin;%PATH%"
set "CONDA_PREFIX=%_ENV%"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo Launching Botty ...
"%PYTHON%" "%BOTTY_DIR%src\main.py"
pause
