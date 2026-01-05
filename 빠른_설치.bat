@echo off
chcp 65001 >nul
echo ========================================
echo   iParking-Bot 빠른 설치 스크립트
echo ========================================
echo.

:: 현재 디렉토리 확인
echo [1/5] 현재 경로 확인...
cd
echo.

:: Python 설치 확인
echo [2/5] Python 설치 확인 중...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았습니다!
    echo    https://www.python.org/downloads/ 에서 Python을 설치하세요.
    pause
    exit /b 1
)
echo ✅ Python 설치 확인됨
echo.

:: 가상환경 생성
echo [3/5] 가상환경 생성 중...
if exist venv (
    echo ⚠️  venv 폴더가 이미 존재합니다. 건너뛰기...
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ 가상환경 생성 실패!
        pause
        exit /b 1
    )
    echo ✅ 가상환경 생성 완료
)
echo.

:: pip 업그레이드
echo [4/5] pip 업그레이드 중...
call venv\Scripts\activate.bat
python.exe -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo ⚠️  pip 업그레이드 실패했지만 계속 진행합니다...
)
echo ✅ pip 업그레이드 완료
echo.

:: 패키지 설치
echo [5/5] 필수 패키지 설치 중...
pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ 패키지 설치 실패!
    pause
    exit /b 1
)
echo ✅ 패키지 설치 완료
echo.

:: 완료 메시지
echo ========================================
echo   ✅ 설치 완료!
echo ========================================
echo.
echo 다음 명령어로 프로그램을 실행하세요:
echo.
echo   1. 가상환경 활성화:
echo      venv\Scripts\activate
echo.
echo   2. 봇 실행:
echo      cd iparking-bot
echo      python bot_Simple_logic.py
echo.
echo   3. 대시보드 실행:
echo      cd iparking-bot
echo      streamlit run dashboard.py
echo.
pause
