@echo off
chcp 65001 >nul
echo ================================
echo 🚗 iParking 대시보드 시작
echo ================================
echo.

REM 가상환경 활성화
call "venv\Scripts\activate.bat"

REM 하위 폴더로 이동
cd iparking-bot

REM 대시보드 실행
echo 📊 대시보드를 시작합니다...
echo 브라우저가 자동으로 열립니다.
echo.
streamlit run dashboard.py

pause
