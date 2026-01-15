@echo off
chcp 65001 >nul
title iParking 디버그 모드

echo ════════════════════════════════════════════════════════════
echo  🔍 iParking 디버그 모드
echo ════════════════════════════════════════════════════════════
echo.
echo  이 창은 문제 해결을 위한 디버그 모드입니다.
echo  에러 메시지를 확인할 수 있습니다.
echo.
echo ════════════════════════════════════════════════════════════
echo.

REM 현재 위치 확인
echo [1/5] 현재 위치 확인
echo 현재 디렉토리: %CD%
echo 배치 파일 위치: %~dp0
echo.

REM 가상환경 확인
echo [2/5] 가상환경 확인
if exist "venv\Scripts\activate.bat" (
    echo ✅ 가상환경 발견: venv\Scripts\activate.bat
) else (
    echo ❌ 가상환경 없음!
    echo    해결 방법: '빠른_설치.bat' 실행
    pause
    exit /b 1
)
echo.

REM 하위 폴더 확인
echo [3/5] iparking-bot 폴더 확인
if exist "iparking-bot" (
    echo ✅ iparking-bot 폴더 발견
) else (
    echo ❌ iparking-bot 폴더 없음!
    echo    현재 위치가 잘못되었을 수 있습니다.
    pause
    exit /b 1
)
echo.

REM 필수 파일 확인
echo [4/5] 필수 파일 확인
if exist "iparking-bot\dashboard.py" (
    echo ✅ dashboard.py 발견
) else (
    echo ❌ dashboard.py 없음!
)

if exist "iparking-bot\Last update_parkingbot.py" (
    echo ✅ Last update_parkingbot.py 발견
) else (
    echo ❌ Last update_parkingbot.py 없음!
)

if exist "iparking-bot\logger_helper.py" (
    echo ✅ logger_helper.py 발견
) else (
    echo ⚠️  logger_helper.py 없음 (로그 기능 제한)
)
echo.

REM Python 버전 확인
echo [5/5] Python 버전 확인
call "venv\Scripts\activate.bat"
python --version
echo.

echo ════════════════════════════════════════════════════════════
echo  ✅ 모든 검사 완료!
echo ════════════════════════════════════════════════════════════
echo.
echo  문제가 없다면 '통합_실행.bat' 또는 'start.bat'를 실행하세요.
echo.
echo  문제가 있다면 위의 ❌ 표시를 확인하세요.
echo.
pause
