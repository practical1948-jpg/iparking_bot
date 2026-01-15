# 터미널 출력을 파일에도 동시에 저장하는 헬퍼
import sys
from datetime import datetime
import os

class DualLogger:
    """터미널과 파일에 동시에 출력"""
    
    def __init__(self, log_dir="logs"):
        self.terminal = sys.stdout
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 오늘 날짜로 로그 파일 생성
        today = datetime.now().strftime('%Y%m%d')
        self.log_file = os.path.join(log_dir, f"bot_{today}.log")
        self.file = open(self.log_file, 'a', encoding='utf-8')
    
    def write(self, message):
        """터미널과 파일에 동시 출력"""
        self.terminal.write(message)
        self.file.write(message)
        self.file.flush()  # 즉시 파일에 쓰기
    
    def flush(self):
        self.terminal.flush()
        self.file.flush()
    
    def close(self):
        self.file.close()

def enable_dual_logging():
    """이 함수를 호출하면 모든 print가 파일에도 저장됨"""
    sys.stdout = DualLogger()
    print(f"✅ 로깅 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

def disable_dual_logging():
    """원래대로 복구"""
    if hasattr(sys.stdout, 'close'):
        sys.stdout.close()
    sys.stdout = sys.__stdout__

# 사용법:
# from logger_helper import enable_dual_logging
# enable_dual_logging()  # 이제부터 모든 print가 파일에도 저장됨
