"""
Firebase Firestore 연동 헬퍼 모듈
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
from pathlib import Path

# Firebase 초기화 상태
_initialized = False
_db = None

def initialize_firebase():
    """Firebase 초기화"""
    global _initialized, _db
    
    if _initialized:
        return _db
    
    try:
        # 인증 파일 경로
        cred_path = Path(__file__).parent / "firebase-credentials.json"
        
        if not cred_path.exists():
            print(f"⚠️ Firebase 인증 파일을 찾을 수 없습니다: {cred_path}")
            return None
        
        # Firebase 초기화
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        
        # Firestore 클라이언트
        _db = firestore.client()
        _initialized = True
        
        print("✅ Firebase 초기화 완료!")
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
    """
    주차 등록 데이터를 Firestore에 저장
    
    Args:
        data (dict): 저장할 데이터
            - 회차 (int)
            - 번호 (int)
            - 성함 (str)
            - 차량번호 (str)
            - 상태 (str)
            - 처리시간 (str)
            - 데이터소스 (str): "주차 명단" 또는 "일일 등록"
            - 비고 (str, optional): 비고 메모
    
    Returns:
        bool: 성공 여부
    """
    try:
        db = get_db()
        if not db:
            return False
        
        # 오늘 날짜
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 문서 ID: 날짜_데이터소스_번호 (충돌 방지)
        data_source = data.get('데이터소스', '주차 명단')
        source_prefix = '주차' if '주차' in data_source else '일일'
        doc_id = f"{today}_{source_prefix}_{data.get('번호', 0):03d}"
        
        # 타임스탬프 추가
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        data['날짜'] = today
        
        # 비고 필드가 없으면 빈 문자열로 초기화
        if '비고' not in data:
            data['비고'] = ''
        
        # Firestore에 저장
        db.collection('parking_records').document(doc_id).set(data, merge=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Firebase 저장 실패: {e}")
        return False

def get_parking_records(date=None):
    """
    주차 등록 데이터 조회
    
    Args:
        date (str, optional): 조회할 날짜 (YYYY-MM-DD). None이면 오늘.
    
    Returns:
        list: 주차 등록 데이터 리스트
    """
    try:
        db = get_db()
        if not db:
            return []
        
        # 날짜 설정
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Firestore 쿼리
        docs = db.collection('parking_records')\
                 .where('날짜', '==', date)\
                 .order_by('번호')\
                 .stream()
        
        # 데이터 변환
        records = []
        for doc in docs:
            data = doc.to_dict()
            records.append(data)
        
        return records
        
    except Exception as e:
        print(f"❌ Firebase 조회 실패: {e}")
        return []

def get_all_dates():
    """저장된 모든 날짜 목록 조회"""
    try:
        db = get_db()
        if not db:
            return []
        
        # 모든 문서에서 날짜 필드 추출
        docs = db.collection('parking_records').stream()
        
        dates = set()
        for doc in docs:
            data = doc.to_dict()
            if '날짜' in data:
                dates.add(data['날짜'])
        
        return sorted(list(dates), reverse=True)
        
    except Exception as e:
        print(f"❌ Firebase 날짜 조회 실패: {e}")
        return []

def check_record_exists(date, number, data_source='주차 명단'):
    """
    특정 날짜와 번호의 데이터가 Firebase에 존재하는지 확인
    
    Args:
        date (str): 날짜 (YYYY-MM-DD)
        number (int): 번호
        data_source (str): 데이터소스 ('주차 명단' 또는 '일일 등록')
    
    Returns:
        bool: 존재 여부
    """
    try:
        db = get_db()
        if not db:
            return False
        
        # 문서 ID (데이터소스 포함)
        source_prefix = '주차' if '주차' in data_source else '일일'
        doc_id = f"{date}_{source_prefix}_{number:03d}"
        
        # 문서 존재 확인
        doc = db.collection('parking_records').document(doc_id).get()
        return doc.exists
        
    except Exception as e:
        print(f"❌ Firebase 체크 실패: {e}")
        return False

def update_remark(date, number, data_source, remark):
    """
    특정 데이터의 비고 업데이트
    
    Args:
        date (str): 날짜 (YYYY-MM-DD)
        number (int): 번호
        data_source (str): 데이터소스 ('주차 명단' 또는 '일일 등록')
        remark (str): 비고 내용
    
    Returns:
        bool: 성공 여부
    """
    try:
        db = get_db()
        if not db:
            return False
        
        # 문서 ID
        source_prefix = '주차' if '주차' in data_source else '일일'
        doc_id = f"{date}_{source_prefix}_{number:03d}"
        
        # 비고만 업데이트
        db.collection('parking_records').document(doc_id).update({
            '비고': remark,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return True
        
    except Exception as e:
        print(f"❌ Firebase 비고 업데이트 실패: {e}")
        return False

def delete_old_records(days=30):
    """오래된 데이터 삭제 (일정 기간 이상)"""
    try:
        db = get_db()
        if not db:
            return False
        
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 오래된 데이터 조회
        docs = db.collection('parking_records')\
                 .where('날짜', '<', cutoff_date)\
                 .stream()
        
        # 삭제
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        
        print(f"✅ {deleted_count}개의 오래된 데이터 삭제 완료")
        return True
        
    except Exception as e:
        print(f"❌ Firebase 삭제 실패: {e}")
        return False
