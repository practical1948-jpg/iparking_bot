"""
Firebase Firestore 연동 헬퍼 모듈
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
from pathlib import Path
import pytz

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
        # 인증 파일 경로
        cred_path = Path(__file__).parent / "firebase-credentials.json"
        
        if not cred_path.exists():
            print(f"⚠️ Firebase 인증 파일을 찾을 수 없습니다: {cred_path}")
            return None
        
        # Firebase 초기화 (이미 초기화되어 있으면 기존 앱 사용)
        try:
            # 기존 앱이 있는지 확인
            firebase_admin.get_app()
            print("ℹ️ Firebase 앱이 이미 초기화되어 있습니다.")
        except ValueError:
            # 앱이 없으면 새로 초기화
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)
            print("✅ Firebase 앱 초기화 완료!")
        
        # Firestore 클라이언트
        _db = firestore.client()
        _initialized = True
        
        print("✅ Firebase 연결 완료!")
        return _db
        
    except Exception as e:
        print(f"❌ Firebase 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
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
        
        # 서울 표준시 기준 오늘 날짜
        today = get_kst_now().strftime('%Y-%m-%d')
        
        # 문서 ID: 날짜_데이터소스_번호 (같은 번호 = 같은 차량)
        # 여러 회차에서 같은 번호를 처리하면 업데이트됨 (최신 상태 유지)
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
        
        # Firestore 쿼리 (단일 where 조건, order_by는 Python에서 처리)
        docs = db.collection('parking_records')\
                 .where('날짜', '==', date)\
                 .stream()
        
        # 데이터 변환
        records = []
        for doc in docs:
            data = doc.to_dict()
            records.append(data)
        
        # Python에서 번호로 정렬
        records.sort(key=lambda x: x.get('번호', 0))
        
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

def check_record_exists_by_car(date, car_number, data_source='주차 명단'):
    """
    특정 날짜와 차량번호로 데이터가 Firebase에 존재하는지 확인
    
    Args:
        date (str): 날짜 (YYYY-MM-DD)
        car_number (str): 차량번호
        data_source (str): 데이터소스 ('주차 명단' 또는 '일일 등록')
    
    Returns:
        bool: 존재 여부
    """
    try:
        db = get_db()
        if not db:
            return False
        
        # 모든 문서 가져오기 (where 절 사용 안 함, 최대 1000개)
        docs = db.collection('parking_records').limit(1000).stream()
        
        # Python에서 필터링 (날짜 + 차량번호 + 데이터소스)
        for doc in docs:
            data = doc.to_dict()
            if (data.get('날짜') == date and 
                data.get('차량번호') == car_number and 
                data.get('데이터소스') == data_source):
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Firebase 차량번호 체크 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_existing_record_by_car(date, car_number, data_source='주차 명단'):
    """
    특정 날짜와 차량번호로 기존 레코드 조회 (상태 확인용)
    
    Args:
        date (str): 날짜 (YYYY-MM-DD)
        car_number (str): 차량번호
        data_source (str): 데이터소스 ('주차 명단' 또는 '일일 등록')
    
    Returns:
        dict or None: 기존 레코드 (있으면), 없으면 None
    """
    try:
        db = get_db()
        if not db:
            return None
        
        print(f"  🔍 Firebase 조회 중... (날짜: {date}, 차량: {car_number[:4]}****)")
        
        # 문서 ID 기반 직접 조회 시도 (가장 빠름)
        source_prefix = '주차' if '주차' in data_source else '일일'
        
        # 가능한 문서 ID 패턴 확인 (번호는 알 수 없으므로 컬렉션 조회 필요)
        # 최근 데이터만 조회 (오늘/어제)
        from datetime import datetime, timedelta
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        date_range = [
            today.strftime('%Y-%m-%d'),
            yesterday.strftime('%Y-%m-%d')
        ]
        
        # 최근 2일치만 조회
        docs = db.collection('parking_records').limit(500).stream()
        
        count = 0
        for doc in docs:
            count += 1
            data = doc.to_dict()
            if (data.get('날짜') == date and 
                data.get('차량번호') == car_number and 
                data.get('데이터소스') == data_source):
                print(f"  ✅ 기존 레코드 발견: {data.get('상태', '?')} (조회한 문서: {count}개)")
                return data  # 전체 레코드 반환
        
        print(f"  ℹ️ 신규 차량 (기존 레코드 없음, 조회한 문서: {count}개)")
        return None
        
    except Exception as e:
        print(f"  ❌ Firebase 레코드 조회 실패: {e}")
        return None

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

def clean_today_orphaned_records(today_car_numbers, data_source='주차 명단'):
    """
    오늘 날짜의 데이터 중 CSV에 없는 차량번호(고아 데이터) 삭제
    
    Args:
        today_car_numbers (list): 현재 CSV에 있는 차량번호 리스트
        data_source (str): 데이터소스
    
    Returns:
        int: 삭제된 데이터 개수
    """
    try:
        db = get_db()
        if not db:
            return 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 오늘 날짜의 모든 데이터 조회 (단일 where 조건)
        docs = db.collection('parking_records')\
                 .where('날짜', '==', today)\
                 .stream()
        
        deleted_count = 0
        for doc in docs:
            data = doc.to_dict()
            car_number = data.get('차량번호', '')
            doc_data_source = data.get('데이터소스', '')
            
            # 데이터소스가 일치하고, CSV에 없는 차량번호면 삭제
            if doc_data_source == data_source and car_number not in today_car_numbers:
                doc.reference.delete()
                deleted_count += 1
                print(f"  🗑️ 고아 데이터 삭제: {car_number}")
        
        if deleted_count > 0:
            print(f"✅ {deleted_count}개의 고아 데이터 삭제 완료")
        
        return deleted_count
        
    except Exception as e:
        print(f"❌ Firebase 고아 데이터 삭제 실패: {e}")
        return 0
