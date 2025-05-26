@echo off
title Starting J.A.R.V.I.S. Virtual Assistant
echo ------------------------------------------
echo 🤖 Launching J.A.R.V.I.S. Virtual Assistant
echo ------------------------------------------

:: Set the working directory to where jp.py is located
cd /d "%~dp0"

:: Optional: Activate virtual environment if it exists
IF EXIST venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: Run the Python script
python main.py

:: Wait for user input before closing
echo ------------------------------------------
echo Press any key to exit...
pause >nul