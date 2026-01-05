@echo off
chcp 65001 >nul
echo ========================================
echo 차량번호 정형화 프로그램
echo ========================================
echo.

if "%~1"=="" (
    echo 사용 방법: 차량번호_정형화.bat "CSV파일경로"
    echo.
    echo 예시:
    echo   차량번호_정형화.bat "(신규)주차등록(응답) - 차량_DB 시트.csv"
    echo.
    pause
    exit /b
)

python 차량번호_정형화.py "%~1"

pause

