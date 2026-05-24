@echo off
setlocal enabledelayedexpansion

set "BOTTY_DIR=%~dp0"
cd /d "%BOTTY_DIR%"

call "%BOTTY_DIR%find_python.bat"

:: Derive conda.exe from the botty python.exe path:
::   envs\botty\python.exe  ->  envs\botty  ->  envs  ->  miniforge3  ->  Scripts\conda.exe
for %%F in ("%PYTHON%") do set "_ENV=%%~dpF"
set "_ENV=%_ENV:~0,-1%"
for %%F in ("%_ENV%") do set "_ENVS=%%~dpF"
set "_ENVS=%_ENVS:~0,-1%"
for %%F in ("%_ENVS%") do set "_ROOT=%%~dpF"
set "_ROOT=%_ROOT:~0,-1%"
set "_CONDA=%_ROOT%\Scripts\conda.exe"

echo Launching Botty ...
if exist "%_CONDA%" (
    :: conda run activates the full environment (PATH, DLL dirs, etc.)
    :: exactly like "conda activate botty" - guaranteed to find all DLLs.
    "%_CONDA%" run -n botty --no-capture-output python "%BOTTY_DIR%src\main.py"
) else (
    echo WARNING: conda.exe not found at %_CONDA%, falling back to direct launch.
    "%PYTHON%" "%BOTTY_DIR%src\main.py"
)
pause
