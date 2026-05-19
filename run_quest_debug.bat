@echo off
setlocal
set "PYTHON=C:\Users\%USERNAME%\miniforge3\envs\botty\python.exe"
if exist "%PYTHON%" (
    cd /d "%~dp0"
    %PYTHON% quest_debug.py
) else (
    echo ERROR: Could not find botty Python.
    echo Run: conda activate botty first.
    pause
)
