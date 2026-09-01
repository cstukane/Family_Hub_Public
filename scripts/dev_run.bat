@echo off
REM Development startup script for Family Hub
REM This script starts the Family Hub UI in one go

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
echo Starting Family Hub on port 5000...
start "Family Hub" cmd /c "python app.py"

REM Give the app a moment to start
timeout /t 3 /nobreak >nul

REM Launch the UI in Chrome
echo Launching Family Hub UI...
call scripts\start_chrome_win.bat

echo.
echo Development environment started!
echo Press any key to exit and stop all services...
pause >nul
