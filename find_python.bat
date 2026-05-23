@echo off
:: Shared conda environment detection for Botty
:: Source this file from your .bat scripts:  call find_python.bat
:: On return, %PYTHON% will be set to the botty env python.exe or the script will exit.

if defined PYTHON goto :_find_python_done

for %%C in (
    "C:\Users\%USERNAME%\miniforge3\envs\botty\python.exe"
    "C:\Users\%USERNAME%\miniconda3\envs\botty\python.exe"
    "C:\Users\%USERNAME%\anaconda3\envs\botty\python.exe"
    "C:\ProgramData\miniforge3\envs\botty\python.exe"
    "C:\ProgramData\miniconda3\envs\botty\python.exe"
    "C:\ProgramData\anaconda3\envs\botty\python.exe"
) do (
    if exist %%C (
        set "PYTHON=%%~C"
        goto :_find_python_done
    )
)

echo ERROR: Could not find botty conda environment.
echo Run install.bat first.
pause
exit /b 1

:_find_python_done
