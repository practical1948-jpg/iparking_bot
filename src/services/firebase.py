"""
Firebase Firestore 연동 서비스 모듈
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz
from pathlib import Path
import sys
import os

# 프로젝트 루트 경로 추가 (config 모듈 import를 위해)
# src/services/firebase.py -> .../iparking-bot/src/services -> .../iparking-bot
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from config import settings
except ImportError:
    # fallback if run directly or path issue
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from config import settings

# 서울 표준시 타임존
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """서울 표준시 현재 시간 반환"""
    return datetime.now(KST)

# Firebase 초기화 상태
_initialized = False
_db = None

def initialize_firebase():
    """Firebase 초기화"""
    global _initialized, _db
    
    if _initialized:
        return _db
    
    try:
        cred_path = Path(settings.FIREBASE_CRED_PATH)
        
        if not cred_path.exists():
            print(f"⚠️ Firebase 인증 파일을 찾을 수 없습니다: {cred_path}")
            return None
        
        try:
            firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)
        
        _db = firestore.client()
        _initialized = True
        
        return _db
        
    except Exception as e:
        print(f"❌ Firebase 초기화 실패: {e}")
        return None

def get_db():
    """Firestore 데이터베이스 인스턴스 가져오기"""
    global _db
    if not _initialized:
        _db = initialize_firebase()
    return _db

def save_parking_record(data):
    """주차 등록 데이터를 Firestore에 저장"""
    try:
        db = get_db()
        if not db: return False
        
        today = get_kst_now().strftime('%Y-%m-%d')
        data_source = data.get('데이터소스', '주차 명단')
        source_prefix = '주차' if '주차' in data_source else '일일'
        doc_id = f"{today}_{source_prefix}_{data.get('번호', 0):03d}"
        
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        data['날짜'] = today
        if '비고' not in data:
            data['비고'] = ''
        
        db.collection('parking_records').document(doc_id).set(data, merge=True)
        return True
    except Exception as e:
        print(f"❌ Firebase 저장 실패: {e}")
        return False

def get_parking_records(date=None):
    """주차 등록 데이터 조회"""
    try:
        db = get_db()
        if not db: return []
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜 내림차순 정렬을 위해 쿼리
        docs = db.collection('parking_records').where('날짜', '==', date).stream()
        
        records = []
        for doc in docs:
            records.append(doc.to_dict())
        
        records.sort(key=lambda x: x.get('번호', 0))
        return records
    except Exception as e:
        print(f"❌ Firebase 조회 실패: {e}")
        return []

def get_processed_cars_today(data_source='주차 명단'):
    """오늘 이미 처리된 차량번호 조회 (캐싱용)"""
    try:
        db = get_db()
        if not db: return {}
        
        today = get_kst_now().strftime('%Y-%m-%d')
        docs = db.collection('parking_records').where('날짜', '==', today).stream()
        
        processed_cars = {}
        for doc in docs:
            data = doc.to_dict()
            if data.get('데이터소스') == data_source and data.get('차량번호'):
                processed_cars[data.get('차량번호')] = data.get('상태', '')
        
        return processed_cars
    except Exception as e:
        print(f"❌ Firebase 캐시 조회 실패: {e}")
        return {}

def update_remark(date, number, data_source, remark):
    """비고 업데이트"""
    try:
        db = get_db()
        if not db: return False
        
        source_prefix = '주차' if '주차' in data_source else '일일'
        doc_id = f"{date}_{source_prefix}_{number:03d}"
        
        db.collection('parking_records').document(doc_id).update({
            '비고': remark,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        print(f"❌ 비고 업데이트 실패: {e}")
        return False

    # 여기서는 간단히 구현
    return False


def update_bot_heartbeat(status="Alive", message=""):
    """봇의 현재 상태와 타임스탬프를 Firebase에 기록"""
    try:
        db = get_db()
        if not db: return False
        
        doc_ref = db.collection('bot_status').document('main_bot')
        doc_ref.set({
            'status': status,
            'last_heartbeat': firestore.SERVER_TIMESTAMP,
            'message': message,
            'hostname': os.environ.get('COMPUTERNAME', 'Unknown')
        }, merge=True)
        return True
    except Exception as e:
        print(f"❌ 하트비트 업데이트 실패: {e}")
        return False


def get_bot_status():
    """Firebase에서 봇의 현재 상태와 마지막 하트비트 시간을 조회"""
    try:
        db = get_db()
        if not db: return None
        
        doc = db.collection('bot_status').document('main_bot').get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"❌ 봇 상태 조회 실패: {e}")
        return None

# 필요한 경우 추가 함수 마이그레이션...
