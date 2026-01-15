@echo off
chcp 65001 >nul
echo ================================
echo 🤖 iParking 봇 시작
echo ================================
echo.

REM 가상환경 활성화
call "venv\Scripts\activate.bat"

REM 하위 폴더로 이동
cd iparking-bot

REM 봇 실행
echo 🚀 주차권 등록 봇을 시작합니다...
echo.
python "Last update_parkingbot.py"

pause
