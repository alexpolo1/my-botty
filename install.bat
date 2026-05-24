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

:: Prepend conda DLL dirs to PATH at the process level so the Windows DLL
:: loader finds tesseract51.dll's transitive deps (leptonica, zlib, etc.)
:: when ctypes loads it. os.environ['PATH'] set from inside Python is too late.
for %%F in ("%PYTHON%") do set "_CONDA_ENV=%%~dpF"
set "_CONDA_ENV=%_CONDA_ENV:~0,-1%"
set "PATH=%_CONDA_ENV%\Library\bin;%_CONDA_ENV%\Library\mingw-w64\bin;%_CONDA_ENV%\Library\usr\bin;%PATH%"

:: --- Force-reinstall the tesserocr wheel so the correct binary is always used ---
echo.
echo Installing tesserocr wheel...
"%PYTHON%" -m pip install --force-reinstall "%~dp0dependencies\tesserocr-2.5.2-cp310-cp310-win_amd64.whl" >nul 2>&1

:: --- Smoke test: import key dependencies ---
echo.
echo Verifying dependencies...
"%PYTHON%" -c "import os,sys,ctypes;dirs=[d for d in [os.path.join(sys.prefix,'Library',x) for x in ['bin','mingw-w64\\bin','usr\\bin']] if os.path.isdir(d)];[os.add_dll_directory(d) for d in dirs];os.environ.__setitem__('PATH',os.pathsep.join(dirs)+os.pathsep+os.environ.get('PATH',''));t=os.path.join(sys.prefix,'Library','bin','tesseract51.dll');ctypes.WinDLL(t) if os.path.isfile(t) else None;import cv2,mss,numpy,tesserocr,discord,transitions,rapidfuzz" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Dependency check failed. Running diagnostics...
    echo.
    "%PYTHON%" -c "import os,sys,ctypes; lb=os.path.join(sys.prefix,'Library','bin'); dlls=[f for f in (os.listdir(lb) if os.path.isdir(lb) else []) if any(k in f.lower() for k in ['tess','lepton'])]; print('  Tesseract DLLs in Library/bin:',dlls or 'NONE'); dirs=[d for d in [os.path.join(sys.prefix,'Library',x) for x in ['bin','mingw-w64\\bin','usr\\bin']] if os.path.isdir(d)]; [os.add_dll_directory(d) for d in dirs]; os.environ.__setitem__('PATH',os.pathsep.join(dirs)+os.pathsep+os.environ.get('PATH','')); t=os.path.join(lb,'tesseract51.dll'); r=ctypes.WinDLL(t) if os.path.isfile(t) else 'missing'; print('  ctypes tesseract51.dll:',type(r).__name__); __import__('tesserocr'); print('  tesserocr import: OK')" 2>&1
    echo.
    echo *** Do NOT run "pip install tesserocr" manually - it builds from source and
    echo *** will always fail on Windows. Re-run install.bat to fix dependencies.
) else (
    echo All key dependencies verified.
)

echo.
echo ============================================
echo  Installation complete!
echo  Run botty with:  run_botty.bat
echo ============================================
echo.
pause
