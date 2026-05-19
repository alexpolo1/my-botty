@echo off
echo === D2R Quick Capture ===
echo Run this, D2R must be visible
echo Press ENTER when D2R is ready...
pause >nul

call C:\Users\alex\miniforge3\condabin\condactivate.bat botty
C:\Users\alex\miniforge3\envs\botty\python.exe C:\Users\alex\Downloads\my-botty\asset_extractor.py
