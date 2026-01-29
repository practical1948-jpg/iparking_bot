import os
from pathlib import Path

# =============================================================================
# 🔐 계정 설정 (사용자 수정 가능)
# =============================================================================
ACCOUNTS = [
    {"username": "dreamcb01", "password": "dreamcb01"},
    {"username": "dreamcb02", "password": "dreamcb02"},
    {"username": "dreamcb03", "password": "dreamcb03"}
]

# =============================================================================
# 📁 경로 설정
# =============================================================================
# 프로젝트 루트 디렉토리 (config 폴더의 상위 폴더)
BASE_DIR = Path(__file__).resolve().parent.parent

# 데이터 파일 경로
DATA_DIR = BASE_DIR / "주차_DB_파일"
LOG_DIR = BASE_DIR / "logs"
EXECUTION_LOG_PATH = BASE_DIR / "file_execution_log.json"

# Firebase 인증 파일 경로
FIREBASE_CRED_PATH = BASE_DIR / "iparking-bot" / "firebase-credentials.json"  # 기존 위치 유지 또는 이동 필요

# =============================================================================
# 🌐 크롬 / 셀레니움 설정
# =============================================================================
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_DIR = r"C:\chrome_debug_temp"
IPARKING_URL = "http://members.iparking.co.kr/html/login.html#!"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# =============================================================================
# ⚙️ 기타 설정
# =============================================================================
# 대시보드 자동 새로고침 간격 (초)
DASHBOARD_REFRESH_RATE = 10
