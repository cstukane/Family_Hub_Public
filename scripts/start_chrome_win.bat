@echo off
REM Windows dev launcher script for Family Hub
REM Starts Chromium/Chrome in app mode pointing to the hub UI

REM Set Chrome path - prefer full path if Chrome is installed in default location
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"

REM Check if Chrome exists at the default location, otherwise try to use chrome from PATH
if exist "%CHROME_PATH%" (
    echo Using Chrome from default installation: %CHROME_PATH%
) else (
    echo Chrome not found at default location, attempting to use chrome from PATH...
    set "CHROME_PATH=chrome"
)

REM Launch Chrome in app mode with appropriate flags
REM --app runs as a standalone window without address bar
REM --disable-infobars prevents info bars from appearing
REM --noerrdialogs suppresses error dialogs
echo Starting Family Hub UI in Chrome app mode...
"%CHROME_PATH%" --app=http://127.0.0.1:5000 --disable-infobars --noerrdialogs --window-size=1280,720 --disable-session-crashed-bubble

echo Chrome window closed or failed to start.