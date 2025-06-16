@echo off
REM =================================================================
REM  Startup script for the Local Project Server on Windows
REM =================================================================

ECHO Starting the Local Project Server...
ECHO This will open the Python script and may prompt for folder selection.

REM Runs the python script. Assumes python is in your PATH.
REM The script name is hardcoded here. If you rename it, change it here too.
python _TempServerMAKER.py

ECHO.
ECHO Server has been shut down. Press any key to close this window.
pause