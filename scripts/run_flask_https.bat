@echo off
REM Launch the Flask app with HTTPS using a local certificate.

setlocal

REM Adjust these paths to point at your certificate and private key.
set "CERT_PATH=%USERPROFILE%\.family-hub\cert.pem"
set "KEY_PATH=%USERPROFILE%\.family-hub\key.pem"

REM Optional: uncomment if you need to pin the host/port via environment variables.
REM set "FLASK_RUN_HOST=127.0.0.1"
REM set "FLASK_RUN_PORT=5000"

REM Activate the virtual environment if it exists.
if exist "..\.\venv\Scripts\activate.bat" (
    call "..\.\venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

REM Run Flask with the specified certificate and key.
python run_socketio.py --host=127.0.0.1 --port=5000 --cert "%CERT_PATH%" --key "%KEY_PATH%"

endlocal
