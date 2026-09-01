@echo off
REM Development startup script for Family Hub
REM This script starts the hub app, media launcher, and the UI in one go

echo Starting Family Hub development environment...
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

REM Activate the virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated.
) else (
    echo Warning: Virtual environment (.venv) not found. Make sure to run: python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages from requirements.txt...
    pip install -r requirements.txt
)

echo.
echo Checking if ports 5000 and 7666 are available...
netstat -an | findstr :5000 >nul
if not errorlevel 1 (
    echo Warning: Port 5000 is in use. Hub app may fail to start.
)
netstat -an | findstr :7666 >nul
if not errorlevel 1 (
    echo Warning: Port 7666 is in use. Media launcher may fail to start.
)
echo.

REM Start the hub app in a separate window
echo Starting hub app on port 5000...
start "Family Hub App" cmd /c "python hub_app.py"

REM Give the hub app a moment to start
timeout /t 3 /nobreak >nul

REM Start the media launcher in a separate window
echo Starting media launcher on port 7666...
start "Media Launcher" cmd /c "python media_launcher.py"

REM Give the media launcher a moment to start
timeout /t 3 /nobreak >nul

REM Launch the UI in Chrome
echo Launching Family Hub UI...
call scripts\start_chrome_win.bat

echo.
echo Development environment started!
echo To test: click YouTube icon in the UI
echo To close media: use Controller button or press Ctrl+Shift+X in the main UI
echo.
echo Press any key to exit and stop all services...
pause >nul
