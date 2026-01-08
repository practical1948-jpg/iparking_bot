@echo off
chcp 65001 >nul
title iParking-Bot 배포 패키지 생성
color 0B

echo ========================================
echo   iParking-Bot 배포 패키지 생성
echo ========================================
echo.

:: 현재 스크립트 위치로 이동
cd /d "%~dp0"

:: 배포 폴더 생성
set DEPLOY_DIR=iparking-bot_배포패키지
if exist "%DEPLOY_DIR%" (
    echo 기존 배포 폴더 삭제 중...
    rmdir /s /q "%DEPLOY_DIR%"
)
mkdir "%DEPLOY_DIR%"
echo ✅ 배포 폴더 생성: %DEPLOY_DIR%
echo.

:: 필수 파일 복사
echo [1/5] 필수 파일 복사 중...

:: iparking-bot 폴더 생성
mkdir "%DEPLOY_DIR%\iparking-bot"

:: Python 파일 복사
copy "iparking-bot\bot_Simple_logic.py" "%DEPLOY_DIR%\iparking-bot\" >nul
copy "iparking-bot\dashboard.py" "%DEPLOY_DIR%\iparking-bot\" >nul
copy "iparking-bot\firebase_helper.py" "%DEPLOY_DIR%\iparking-bot\" >nul
echo   ✅ Python 파일 복사 완료

:: 설정 파일 복사 (템플릿)
if exist "iparking-bot\firebase-credentials.json" (
    copy "iparking-bot\firebase-credentials.json" "%DEPLOY_DIR%\iparking-bot\" >nul
    echo   ✅ Firebase 인증 파일 복사 완료
) else (
    echo   ⚠️  Firebase 인증 파일이 없습니다 (수동으로 추가 필요)
)

:: requirements.txt 복사
copy "requirements.txt" "%DEPLOY_DIR%\" >nul
echo   ✅ requirements.txt 복사 완료

:: 배포 스크립트 및 문서 복사
copy "설치_및_실행.bat" "%DEPLOY_DIR%\" >nul
copy "설치_가이드.md" "%DEPLOY_DIR%\" >nul
copy "빠른_설치_가이드.txt" "%DEPLOY_DIR%\" >nul
copy "배포_가이드.md" "%DEPLOY_DIR%\" >nul
copy "환경_설정_체크리스트.md" "%DEPLOY_DIR%\" >nul
copy "README.md" "%DEPLOY_DIR%\" >nul
echo   ✅ 배포 스크립트 및 문서 복사 완료
echo.

:: 주차_DB_파일 폴더 생성 (빈 폴더)
echo [2/5] 폴더 구조 생성 중...
mkdir "%DEPLOY_DIR%\주차_DB_파일" >nul 2>&1
echo   ✅ 주차_DB_파일 폴더 생성 완료
echo.

:: .gitignore 생성 (선택사항)
echo [3/5] .gitignore 생성 중...
(
echo venv/
echo __pycache__/
echo *.pyc
echo *.pyo
echo *.pyd
echo .Python
echo *.log
echo .DS_Store
echo Thumbs.db
) > "%DEPLOY_DIR%\.gitignore"
echo   ✅ .gitignore 생성 완료
echo.

:: 압축 파일 생성
echo [4/5] 압축 파일 생성 중...
set ZIP_NAME=iparking-bot_배포패키지_%date:~0,4%%date:~5,2%%date:~8,2%.zip

:: PowerShell을 사용한 압축 (Windows 10 이상)
powershell -Command "Compress-Archive -Path '%DEPLOY_DIR%\*' -DestinationPath '%ZIP_NAME%' -Force" >nul 2>&1

if exist "%ZIP_NAME%" (
    echo   ✅ 압축 완료: %ZIP_NAME%
) else (
    echo   ⚠️  자동 압축 실패 (수동으로 압축하세요)
    echo   압축할 폴더: %DEPLOY_DIR%
)
echo.

:: 완료 메시지
echo [5/5] 배포 패키지 생성 완료!
echo ========================================
echo.
echo 배포 패키지 위치:
echo   폴더: %CD%\%DEPLOY_DIR%
if exist "%ZIP_NAME%" (
    echo   압축 파일: %CD%\%ZIP_NAME%
)
echo.
echo 배포 방법:
echo   1. %ZIP_NAME% 파일을 다른 컴퓨터로 전송
echo   2. 압축 해제
echo   3. 빠른_설치_가이드.txt 먼저 읽기 (권장)
echo   4. 설치_및_실행.bat 실행
echo.
echo 📚 포함된 문서:
echo   - 빠른_설치_가이드.txt : 5분 안에 설치하는 방법
echo   - 설치_가이드.md : 전체 설치 과정 상세 가이드
echo   - 배포_가이드.md : 배포 관련 정보
echo   - 환경_설정_체크리스트.md : 환경 설정 확인
echo   - README.md : 프로젝트 소개
echo.
echo ⚠️  주의사항:
echo   - firebase-credentials.json 파일이 포함되어 있는지 확인하세요
echo   - 배포 전에 민감한 정보가 없는지 확인하세요
echo   - Python 3.8 이상과 Chrome 브라우저 필요
echo.
pause

