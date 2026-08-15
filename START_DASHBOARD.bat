@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating the project environment...
    python -m venv .venv
    if errorlevel 1 goto :error

    echo Installing project requirements...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

echo Starting Energy Market Risk Monitor...
echo Your browser should open automatically. Press Ctrl+C here to stop the app.
".venv\Scripts\python.exe" -m streamlit run app.py
goto :eof

:error
echo.
echo Setup failed. Confirm that Python 3.10 or newer is installed and available as "python".
pause
exit /b 1

