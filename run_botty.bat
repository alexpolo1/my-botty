@echo off
setlocal

:: Detect which conda we have and activate the botty env
set "PYTHON="
if exist "C:\Users\%USERNAME%\miniforge3\envs\botty\python.exe" set "PYTHON=C:\Users\%USERNAME%\miniforge3\envs\botty\python.exe"
if exist "C:\Users\%USERNAME%\miniconda3\envs\botty\python.exe" set "PYTHON=C:\Users\%USERNAME%\miniconda3\envs\botty\python.exe"
if exist "C:\Users\%USERNAME%\anaconda3\envs\botty\python.exe" set "PYTHON=C:\Users\%USERNAME%\anaconda3\envs\botty\python.exe"

if "%PYTHON%"=="" (
echo ERROR: Could not find botty conda environment.
echo Create it first: conda env create -f environment.yml
pause
exit /b 1
)

echo Launching Botty ...
%PYTHON% src\main.py
pause
