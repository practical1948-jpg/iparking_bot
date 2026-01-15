@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ════════════════════════════════════════════════════════════
REM  🚗 iParking 자동화 시스템 통합 실행 배치
REM ════════════════════════════════════════════════════════════

title iParking 자동화 시스템

REM 현재 배치 파일 경로 저장
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ═══════════════════════════════════════════════════════════
echo  🚗 iParking 자동화 시스템 시작
echo ═══════════════════════════════════════════════════════════
echo.

REM ────────────────────────────────────────────────────────────
REM  [1/2] 대시보드 실행 (별도 창)
REM ────────────────────────────────────────────────────────────

echo [1/2] 📊 대시보드를 백그라운드에서 실행합니다...
echo        새 창이 열리고 브라우저가 자동으로 시작됩니다.
echo.

REM 대시보드 실행 스크립트 생성 (임시)
(
echo @echo off
echo chcp 65001 ^>nul
echo title iParking Dashboard
echo.
echo ═══════════════════════════════════════════════════════════
echo  📊 iParking 대시보드 실행 중
echo ═══════════════════════════════════════════════════════════
echo.
echo 브라우저가 곧 열립니다...
echo Local URL: http://localhost:8501
echo.
echo ───────────────────────────────────────────────────────────
echo  💡 이 창을 닫으면 대시보드가 종료됩니다.
echo     주차 프로그램만 종료하려면 메인 창을 닫으세요.
echo ═══════════════════════════════════════════════════════════
echo.
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
cd /d "%SCRIPT_DIR%iparking-bot"
streamlit run dashboard.py
) > "%TEMP%\iparking_dashboard_temp.bat"

REM 대시보드를 새 창에서 실행
start "iParking Dashboard" cmd /k "%TEMP%\iparking_dashboard_temp.bat"

REM 대시보드 초기화 대기 (3초)
echo        대시보드 초기화 중...
timeout /t 3 /nobreak >nul

echo        ✅ 대시보드가 별도 창에서 실행되었습니다.
echo.

REM ────────────────────────────────────────────────────────────
REM  [2/2] 주차 프로그램 실행 (메인 창)
REM ────────────────────────────────────────────────────────────

echo [2/2] 🤖 주차 프로그램을 시작합니다...
echo.
echo ═══════════════════════════════════════════════════════════
echo.

REM 가상환경 활성화
call "venv\Scripts\activate.bat" 2>nul
if errorlevel 1 (
    echo ❌ 가상환경 활성화 실패!
    echo    빠른_설치.bat을 먼저 실행하세요.
    echo.
    pause
    exit /b 1
)

REM 하위 폴더로 이동
cd /d "%SCRIPT_DIR%iparking-bot" 2>nul
if errorlevel 1 (
    echo ❌ iparking-bot 폴더를 찾을 수 없습니다!
    echo    현재 위치: %CD%
    echo.
    pause
    exit /b 1
)

REM 주차 프로그램 실행
python "bot_Simple_logic.py" 2>nul
if errorlevel 1 (
    echo.
    echo ❌ 주차 프로그램 실행 실패!
    echo    bot_Simple_logic.py 파일을 확인하세요.
    echo.
    pause
    exit /b 1
)

REM ────────────────────────────────────────────────────────────
REM  프로그램 종료 안내
REM ────────────────────────────────────────────────────────────

echo.
echo ═══════════════════════════════════════════════════════════
echo  ✅ 주차 프로그램이 종료되었습니다.
echo ═══════════════════════════════════════════════════════════
echo.
echo  💡 대시보드는 별도 창에서 계속 실행 중입니다.
echo     - 대시보드 종료: "iParking Dashboard" 창을 닫으세요
echo     - 대시보드 주소: http://localhost:8501
echo.
echo  🔄 주차 프로그램만 다시 실행하려면:
echo     '봇_실행.bat' 파일을 사용하세요.
echo.
echo ═══════════════════════════════════════════════════════════
echo.

pause
