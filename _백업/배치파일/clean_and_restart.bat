@echo off
chcp 65001 >nul
echo ========================================
echo   Python 캐시 완전 삭제 및 재시작
echo ========================================
echo.

cd /d "%~dp0"

echo [1] 가상환경 활성화...
call venv\Scripts\activate.bat

echo [2] Python 캐시 삭제 중...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul

echo [3] iparking-bot 폴더로 이동...
cd iparking-bot

echo [4] 대시보드 시작...
echo.
streamlit run dashboard.py

pause
