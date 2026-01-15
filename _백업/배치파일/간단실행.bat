@echo off
REM ===== Simple Start =====

REM Move to script directory
cd /d "%~dp0"

echo Starting iParking System...
echo.

REM Activate venv
call venv\Scripts\activate.bat

REM Run dashboard in new window
start "Dashboard" cmd /k "cd /d %~dp0iparking-bot && streamlit run dashboard.py"

REM Wait 3 seconds
timeout /t 3 /nobreak

REM Run bot
cd /d "%~dp0iparking-bot"
python "bot_Simple_logic.py"

pause
