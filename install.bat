@echo off
setlocal enabledelayedexpansion

:: Always run from the folder this script lives in
cd /d "%~dp0"

echo ============================================
echo  Botty - Dependency Installer
echo ============================================
echo.

:: --- Find conda ---
set "CONDA_EXE="
for %%C in (
    "%USERPROFILE%\miniforge3\Scripts\conda.exe"
    "%USERPROFILE%\miniconda3\Scripts\conda.exe"
    "%USERPROFILE%\anaconda3\Scripts\conda.exe"
    "%ProgramData%\miniforge3\Scripts\conda.exe"
    "%ProgramData%\miniconda3\Scripts\conda.exe"
    "%ProgramData%\anaconda3\Scripts\conda.exe"
) do (
    if exist %%C (
        set "CONDA_EXE=%%~C"
        goto :found_conda
    )
)

echo ERROR: conda not found. Install Miniforge or Miniconda first:
echo   https://github.com/conda-forge/miniforge/releases/latest
echo.
pause
exit /b 1

:found_conda
echo Found conda: %CONDA_EXE%
echo.

:: --- Create or update the botty env ---
"%CONDA_EXE%" env list | findstr /C:"botty" >nul 2>&1
if %errorlevel% equ 0 (
    echo Updating existing 'botty' conda environment...
    "%CONDA_EXE%" env update -f environment.yml --prune
) else (
    echo Creating 'botty' conda environment...
    "%CONDA_EXE%" env create -f environment.yml
)

if %errorlevel% neq 0 (
    echo.
    echo ERROR: conda env create/update failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Installation complete!
echo  Run botty with:  run_botty.bat
echo ============================================
echo.
pause
