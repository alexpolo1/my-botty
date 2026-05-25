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

:: --- Test conda works (catches broken base env, missing pywin32, etc.) ---
echo Testing conda...
"%CONDA_EXE%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: conda found but failed to run. Your conda installation may be broken.
    echo Try re-installing Miniforge: https://github.com/conda-forge/miniforge
    echo.
    pause
    exit /b 1
)
echo conda is working.
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

:: --- Verify botty env has Python ---
set "PYTHON="
for %%C in (
    "%USERPROFILE%\miniforge3\envs\botty\python.exe"
    "%USERPROFILE%\miniconda3\envs\botty\python.exe"
    "%USERPROFILE%\anaconda3\envs\botty\python.exe"
    "%ProgramData%\miniforge3\envs\botty\python.exe"
    "%ProgramData%\miniconda3\envs\botty\python.exe"
    "%ProgramData%\anaconda3\envs\botty\python.exe"
) do (
    if exist %%C (
        set "PYTHON=%%~C"
        goto :env_created
    )
)

echo.
echo ERROR: botty env was created but python.exe was not found.
echo This usually means the env build failed. Check output above.
pause
exit /b 1

:env_created
echo Botty Python: %PYTHON%

:: --- Remove old pip-installed tesserocr wheel if present (we may reinstall from bundled wheel below) ---
echo.
echo Removing old pip-installed tesserocr if present...
"%PYTHON%" -m pip uninstall tesserocr -y >nul 2>&1

:: --- Smoke test via conda run (activates the full env like "conda activate botty") ---
:: This is the only reliable way to ensure all DLL transitive deps are resolved.
echo.
echo Verifying dependencies...
"%CONDA_EXE%" run -n botty python -c "import cv2,mss,numpy,tesserocr,discord,transitions,rapidfuzz" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Dependency check failed. Running diagnostics...
    echo.
    "%CONDA_EXE%" run -n botty python -c "import tesserocr; print('  tesserocr: OK')" 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo tesserocr is missing from conda environment. Trying bundled wheel fallback...
        if exist "dependencies\tesserocr-2.5.2-cp310-cp310-win_amd64.whl" (
            "%CONDA_EXE%" run -n botty python -m pip install --force-reinstall --no-deps "dependencies\tesserocr-2.5.2-cp310-cp310-win_amd64.whl"
            if %errorlevel% neq 0 (
                echo.
                echo ERROR: Bundled tesserocr wheel install failed.
            ) else (
                echo Bundled tesserocr wheel installed, re-checking imports...
                "%CONDA_EXE%" run -n botty python -c "import cv2,mss,numpy,tesserocr,discord,transitions,rapidfuzz" >nul 2>&1
                if %errorlevel% equ 0 (
                    echo All key dependencies verified after wheel fallback.
                    goto :install_done
                )
            )
        ) else (
            echo.
            echo ERROR: Missing fallback wheel:
            echo   dependencies\tesserocr-2.5.2-cp310-cp310-win_amd64.whl
        )
    )
    echo.
    echo *** Do NOT run "pip install tesserocr" manually - it builds from source and
    echo *** will usually fail on Windows. Re-run install.bat to fix dependencies.
) else (
    echo All key dependencies verified.
)

:install_done
echo.
echo ============================================
echo  Installation complete!
echo  Run botty with:  run_botty.bat
echo ============================================
echo.
pause
