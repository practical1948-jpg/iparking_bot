@echo off
chcp 65001 >nul
title iParking-Bot 자동 설치 및 실행
color 0A

echo ========================================
echo   iParking-Bot 자동 설치 및 실행
echo ========================================
echo.

:: 현재 스크립트 위치로 이동
cd /d "%~dp0"
echo [경로 설정] 현재 위치: %CD%
echo.

:: Python 설치 확인
echo [1/7] Python 설치 확인 중...
echo   py 명령어 확인 중...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   py 명령어를 찾을 수 없습니다.
    echo   python 명령어 확인 중...
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ❌ Python이 설치되지 않았습니다!
        echo.
        echo    Python 3.8 이상이 필요합니다.
        echo    https://www.python.org/downloads/ 에서 설치하세요.
        echo.
        echo    💡 권장: Python 3.12 설치
        echo    설치 시 "Add Python to PATH" 옵션을 체크하세요!
        echo.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
    echo   ✅ python 명령어 사용
    python --version
) else (
    set PYTHON_CMD=py
    echo   ✅ py 명령어 사용 (Python Launcher)
    py --version
)
echo ✅ Python 설치 확인됨 (명령어: %PYTHON_CMD%)
echo.

:: Chrome 브라우저 설치 확인
echo [2/7] Chrome 브라우저 설치 확인 중...
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
    echo ✅ Chrome 브라우저 확인됨 (기본 경로)
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
    echo ✅ Chrome 브라우저 확인됨 (x86 경로)
) else (
    echo ⚠️  Chrome 브라우저를 찾을 수 없습니다!
    echo.
    echo    Chrome 브라우저가 필요합니다.
    echo    https://www.google.com/chrome/ 에서 설치하세요.
    echo.
    echo    Chrome 없이는 프로그램이 작동하지 않습니다.
    echo    계속 진행하시겠습니까? (Y/N)
    set /p continue_chrome="> "
    if /i not "%continue_chrome%"=="Y" (
        exit /b 1
    )
)
echo.

:: 가상환경 생성
echo [3/7] 가상환경 생성 중...
if exist venv (
    echo ⚠️  venv 폴더가 이미 존재합니다. 기존 가상환경 사용...
) else (
    if not defined PYTHON_CMD (
        echo ❌ Python 명령어가 설정되지 않았습니다!
        pause
        exit /b 1
    )
    echo   %PYTHON_CMD% -m venv venv 실행 중...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ 가상환경 생성 실패!
        echo    명령어: %PYTHON_CMD% -m venv venv
        pause
        exit /b 1
    )
    echo ✅ 가상환경 생성 완료
)
echo.

:: pip 업그레이드
echo [4/7] pip 업그레이드 중...
call venv\Scripts\activate.bat >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 가상환경 활성화 실패!
    pause
    exit /b 1
)
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo ⚠️  pip 업그레이드 실패했지만 계속 진행합니다...
) else (
    echo ✅ pip 업그레이드 완료
)
echo.

:: 패키지 설치
echo [5/7] 필수 패키지 설치 중...
if not exist requirements.txt (
    echo ❌ requirements.txt 파일을 찾을 수 없습니다!
    pause
    exit /b 1
)
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ❌ 패키지 설치 실패!
    echo    인터넷 연결을 확인하거나 수동으로 설치하세요:
    echo.
    echo    수동 설치 방법:
    echo    1. venv\Scripts\activate
    echo    2. pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo ✅ 패키지 설치 완료
echo.

:: ChromeDriver 자동 설치 확인
echo [6/7] ChromeDriver 설정 확인 중...
echo   Selenium이 자동으로 ChromeDriver를 관리합니다.
echo   첫 실행 시 자동으로 다운로드됩니다.
echo ✅ ChromeDriver 설정 완료
echo.

:: Firebase 인증 파일 확인
echo [7/7] Firebase 설정 확인 중...
if exist "iparking-bot\firebase-credentials.json" (
    echo ✅ Firebase 인증 파일 확인됨
) else (
    echo ⚠️  Firebase 인증 파일이 없습니다.
    echo    iparking-bot\firebase-credentials.json 파일을 추가하세요.
    echo    (없어도 프로그램은 실행되지만 Firebase 기능은 사용할 수 없습니다)
)
echo.

:: 환경 변수 확인
echo.
echo ========================================
echo   환경 설정 확인
echo ========================================
echo.
echo Python 명령어: %PYTHON_CMD%
echo Python 경로: 
where %PYTHON_CMD% 2>nul || echo   (환경 변수에 없음)
echo.
echo Chrome 경로:
if defined CHROME_PATH (
    echo   %CHROME_PATH%
) else (
    echo   (Chrome을 찾을 수 없음)
)
echo.
echo ========================================
echo   설치 완료!
echo ========================================
echo.
echo 실행 메뉴
echo ========================================
echo.
echo 실행할 프로그램을 선택하세요:
echo.
echo   1. 주차권 등록 봇 실행
echo   2. 대시보드 실행 (웹 브라우저)
echo   3. 종료
echo.
set /p choice="번호 입력 (1-3): "

if "%choice%"=="1" (
    echo.
    echo ========================================
    echo   주차권 등록 봇 실행
    echo ========================================
    echo.
    call venv\Scripts\activate.bat
    cd iparking-bot
    python bot_Simple_logic.py
    cd ..
    pause
) else if "%choice%"=="2" (
    echo.
    echo ========================================
    echo   대시보드 실행 중...
    echo ========================================
    echo.
    echo 브라우저가 자동으로 열립니다.
    echo 종료하려면 이 창에서 Ctrl+C를 누르세요.
    echo.
    call venv\Scripts\activate.bat
    cd iparking-bot
    streamlit run dashboard.py
    cd ..
    pause
) else (
    echo.
    echo 프로그램을 종료합니다.
    exit /b 0
)

