@echo off
chcp 65001 >nul
echo ========================================
echo 주차 명단 자동화 프로그램
echo ========================================
echo.

if "%~1"=="" (
    echo 사용 방법: 주차명단_생성.bat "CSV파일경로" [옵션]
    echo.
    echo 예시:
    echo   주차명단_생성.bat "(신규)주차등록(응답) - 차량_DB 시트.csv"
    echo   주차명단_생성.bat "입력.csv" --html-only
    echo.
    pause
    exit /b
)

python 주차명단_자동화.py "%~1" %2 %3

pause

