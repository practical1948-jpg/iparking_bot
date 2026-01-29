import subprocess
import socket
import os
import time
from pathlib import Path
from config import settings

def cleanup_debug_chrome():
    """디버깅 모드로 실행된 Chrome 프로세스 정리"""
    try:
        print("\n기존 디버깅 Chrome 프로세스 확인 중...")
        cmd = 'Get-CimInstance Win32_Process -Filter "name = \'chrome.exe\'" | Where-Object { $_.CommandLine -like "*--remote-debugging-port=' + str(settings.CHROME_DEBUG_PORT) + '*" } | Select-Object ProcessId -ExpandProperty ProcessId'
        result = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True)
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"발견된 디버깅 Chrome 프로세스: {len(pids)}개")
            for pid in pids:
                try:
                    pid = pid.strip()
                    if pid:
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        print(f"  - PID {pid} 종료됨")
                except Exception:
                    pass
            print("기존 디버깅 Chrome 정리 완료")
            time.sleep(2)
        else:
            print("실행 중인 디버깅 Chrome 없음")
    except Exception as e:
        print(f"Chrome 정리 중 오류 (무시): {e}")

def start_chrome_debug_mode():
    """Chrome 디버깅 모드를 시작하는 함수"""
    try:
        # 포트가 이미 사용 중인지 확인
        print(f"포트 {settings.CHROME_DEBUG_PORT} 상태 확인 중...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', settings.CHROME_DEBUG_PORT))
        sock.close()
        
        if result == 0:
            print(f"  ✓ Chrome 디버깅 포트 {settings.CHROME_DEBUG_PORT}가 이미 열려있습니다.")
            print("  → 기존 Chrome 세션을 사용합니다.")
            return True
        
        print("  → 새 Chrome 디버깅 세션을 시작합니다.")
        
        chrome_path = settings.CHROME_PATH
        debug_dir = settings.CHROME_DEBUG_DIR
        iparking_url = settings.IPARKING_URL
        
        # 디버그 디렉토리가 없으면 생성
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Chrome 디버깅 모드 실행 (탭 3개)
        cmd = f'start "" "{chrome_path}" --remote-debugging-port={settings.CHROME_DEBUG_PORT} --user-data-dir="{debug_dir}" "{iparking_url}" "{iparking_url}" "{iparking_url}"'
        print(f"Chrome 디버깅 모드 시작")
        
        subprocess.Popen(cmd, shell=True)
        
        print("Chrome 초기화 및 페이지 로딩 중... (5초 대기)")
        time.sleep(5)
        
        return True
    except Exception as e:
        print(f"Chrome 디버깅 모드 시작 실패: {e}")
        return False
