# 실시간 로그를 파일에 저장하는 봇 (샘플)
import logging
import sys
from datetime import datetime
from firebase_helper import get_db, save_parking_record
import time

# 로그 파일 설정
LOG_DIR = "logs"
import os
os.makedirs(LOG_DIR, exist_ok=True)

# 로거 설정 (콘솔 + 파일 동시 출력)
def setup_logger(car_number):
    """차량별 로그 파일 생성"""
    log_filename = os.path.join(LOG_DIR, f"{car_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logger = logging.getLogger(car_number)
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러 (터미널에도 출력)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 포맷 설정
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename

def process_car_registration(name, car_number):
    """차량 등록 처리 (로깅 포함)"""
    logger, log_file = setup_logger(car_number)
    
    logger.info("=" * 50)
    logger.info(f"🚗 차량 등록 시작: {name} ({car_number})")
    logger.info("=" * 50)
    
    try:
        # 1. Firebase에 초기 상태 저장
        logger.info("📝 Firebase에 데이터 저장 중...")
        data = {
            '회차': 0,
            '번호': int(datetime.now().timestamp()),
            '성함': name,
            '차량번호': car_number,
            '상태': '처리중',
            '처리시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '데이터소스': '일일 등록',
            '비고': '',
            '로그파일': log_file
        }
        
        if save_parking_record(data):
            logger.info("✅ Firebase 저장 완료")
        else:
            logger.error("❌ Firebase 저장 실패")
            return False
        
        # 2. 입차 확인 (시뮬레이션)
        logger.info("🔍 입차 여부 확인 중...")
        time.sleep(2)  # 실제로는 Selenium 동작
        logger.info("✅ 입차 확인 완료")
        
        # 3. 주차권 등록 (시뮬레이션)
        logger.info("🎫 주차권 등록 시작...")
        for i in range(3):
            logger.info(f"  탭 {i+1}/3 처리 중...")
            time.sleep(1)
            logger.info(f"  ✅ 탭 {i+1} 성공")
        
        # 4. 완료 처리
        logger.info("=" * 50)
        logger.info("✅ 모든 처리 완료!")
        logger.info("=" * 50)
        
        # 상태 업데이트
        data['상태'] = '등록성공 (3개 완료)'
        save_parking_record(data)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        data['상태'] = f'실패 ({str(e)})'
        save_parking_record(data)
        return False

if __name__ == "__main__":
    # 터미널에서 실행: python bot_with_logging.py "홍길동" "12가3456"
    if len(sys.argv) >= 3:
        name = sys.argv[1]
        car_number = sys.argv[2]
    else:
        name = input("성함: ")
        car_number = input("차량번호: ")
    
    process_car_registration(name, car_number)
