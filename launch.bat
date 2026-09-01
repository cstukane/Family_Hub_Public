@echo off
REM Family Hub Application Launcher
REM This script ensures the virtual environment is properly used and launches the Family Hub Flask application
REM 
REM Prerequisites:
REM - Python 3.11+ installed
REM - Virtual environment created with dependencies installed
REM - config.yaml properly configured

setlocal enabledelayedexpansion

echo.
echo ================================================
echo    Family Hub Application Launcher
echo ================================================
echo.

REM Change to the application directory
cd /d "%~dp0"

echo Current directory: %cd%
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ and ensure it's in your PATH
    pause
    exit /b 1
)

echo Python version check passed
echo.

REM Load environment variables from .env if present
if exist ".env" (
    echo Loading environment variables from .env
    for /f "usebackq delims=" %%L in (`type ".env"`) do (
        set "LINE=%%L"
        if not "!LINE!"=="" if not "!LINE:~0,1!"=="#" (
            for /f "tokens=1,* delims==" %%a in ("!LINE!") do (
                if not "%%a"=="" set "%%a=%%b"
            )
        )
    )
    echo Environment variables loaded from .env
) else (
    echo WARNING: .env not found. Using existing environment variables.
)
echo.

REM Check for virtual environment and set Python path accordingly
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_PATH=.venv\Scripts\python.exe"
    echo Using virtual environment Python: !PYTHON_PATH!
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_PATH=venv\Scripts\python.exe"
    echo Using virtual environment Python: !PYTHON_PATH!
) else (
    set "PYTHON_PATH=python"
    echo WARNING: No virtual environment found. Using system Python.
    echo Consider running 'python -m venv .venv' and 'pip install -r requirements.txt' first
)

REM Check if required packages are available with the selected Python
echo Checking required packages...
"!PYTHON_PATH!" -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Flask is not installed in the selected Python environment
    echo Please run 'pip install -r requirements.txt' in the appropriate environment
    pause
    exit /b 1
)

"!PYTHON_PATH!" -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyYAML is not installed in the selected Python environment
    echo Please run 'pip install -r requirements.txt' in the appropriate environment
    pause
    exit /b 1
)

"!PYTHON_PATH!" -c "import apscheduler" >nul 2>&1
if errorlevel 1 (
    echo ERROR: APScheduler is not installed in the selected Python environment
    echo Please run 'pip install -r requirements.txt' in the appropriate environment
    pause
    exit /b 1
)

echo Required packages check passed
echo.

REM Check if config.yaml exists
if not exist "config.yaml" (
    echo WARNING: config.yaml not found
    echo Creating a basic config.yaml from the example values...
    echo layout: >nul
    echo   main_view: week_calendar >> config.yaml
    echo   sidebar: [notes, shopping, weather] >> config.yaml
    echo. >> config.yaml
    echo providers: >> config.yaml
    echo   calendar: >> config.yaml
    echo     kind: "ics" >> config.yaml
    echo     ics_url: "https://example.com/family.ics" >> config.yaml
    echo   weather: >> config.yaml
    echo     kind: "open_meteo" >> config.yaml
    echo     location: { lat: 40.90, lon: -74.55 } >> config.yaml
    echo. >> config.yaml
    echo features: >> config.yaml
    echo   voice: false >> config.yaml
    echo   kiosk: false >> config.yaml
    echo   auth: false >> config.yaml
    echo. >> config.yaml
    echo ui: >> config.yaml
    echo   theme: "auto" >> config.yaml
    echo   density: "comfortable" >> config.yaml
    echo. >> config.yaml
    echo security: >> config.yaml
    echo   ssl_enabled: false >> config.yaml
    echo   rate_limit_enabled: true >> config.yaml
    echo   default_rate_limit: "60 per minute" >> config.yaml
    echo   admin_rate_limit: "10 per minute" >> config.yaml
    echo   session_timeout: 3600 >> config.yaml
    echo   secure_headers: true >> config.yaml
    echo Created basic config.yaml
    echo IMPORTANT: Please customize config.yaml with your specific settings
    echo.
)

REM Check if instance directory exists, create if not
if not exist "instance" (
    echo Creating instance directory...
    mkdir instance
    echo Instance directory created
)

echo.

REM Set environment variables for Flask
if not defined FLASK_APP set FLASK_APP=app.py
if not defined FLASK_ENV set FLASK_ENV=development

echo Setting environment variables:
echo   FLASK_APP=%FLASK_APP%
echo   FLASK_ENV=%FLASK_ENV%
echo.

echo ================================================
echo Starting Family Hub Application...
echo ================================================
echo.
echo Access the application at:
echo   HTTP: http://localhost:5000
echo.
echo Press Ctrl+C to stop the application
echo ================================================
echo.

REM Start the Flask application using the specific Python path
"!PYTHON_PATH!" run_socketio.py --host=0.0.0.0 --port=5000

REM If the application stopped due to an error, show it
if errorlevel 1 (
    echo.
    echo ERROR: The application stopped unexpectedly
    echo Check the console output above for error details
    pause
)

endlocal
