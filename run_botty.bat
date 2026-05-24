@echo off
setlocal
set "BOTTY_DIR=%~dp0"
cd /d "%BOTTY_DIR%"

call "%BOTTY_DIR%find_python.bat"

:: Prepend conda DLL dirs to PATH at the process level so the Windows DLL
:: loader finds tesseract51.dll's transitive deps (leptonica, zlib, etc.)
:: when ctypes loads it. os.environ['PATH'] set from inside Python is too late.
for %%F in ("%PYTHON%") do set "_CONDA_ENV=%%~dpF"
set "_CONDA_ENV=%_CONDA_ENV:~0,-1%"
set "PATH=%_CONDA_ENV%\Library\bin;%_CONDA_ENV%\Library\mingw-w64\bin;%_CONDA_ENV%\Library\usr\bin;%PATH%"

echo Launching Botty ...
%PYTHON% "%BOTTY_DIR%src\main.py"
pause
