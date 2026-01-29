"""
CSV 유틸리티 모듈
- 수동 입력 데이터를 CSV 파일 최상단에 추가 (우선처리)
- 파일 잠금 처리로 동시 접근 방지
"""
import os
import csv
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_FOLDER = PROJECT_ROOT / "주차_DB_파일"


def get_latest_db_file():
    """주차_DB_파일 폴더에서 가장 최근 CSV 파일을 찾음"""
    try:
        import glob
        csv_files = glob.glob(str(DB_FOLDER / "*.csv"))
        if not csv_files:
            return None
        return max(csv_files, key=os.path.getmtime)
    except Exception as e:
        print(f"최신 파일 검색 오류: {e}")
        return None


def prepend_to_csv(car_data_list: list, csv_path: str = None) -> tuple:
    """
    수동 입력 데이터를 CSV 최상단에 추가 (우선 처리되도록)
    
    Args:
        car_data_list: [{'성함': '홍길동', '차량번호': '12가3456'}, ...] 형태
        csv_path: 대상 CSV 파일 (없으면 최신 DB 파일 사용)
    
    Returns:
        (success_count, error_count)
    """
    if not csv_path:
        csv_path = get_latest_db_file()
    
    if not csv_path or not os.path.exists(csv_path):
        print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_path}")
        return (0, len(car_data_list))
    
    success_count = 0
    error_count = 0
    
    try:
        # 기존 CSV 읽기
        df_existing = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 컬럼명 정규화
        df_existing.columns = df_existing.columns.str.replace('\n', ' ').str.strip()
        
        # 차량번호 컬럼 찾기
        car_col = None
        for col in df_existing.columns:
            if '차량번호' in col or '차량' in col:
                car_col = col
                break
        if car_col and car_col != '차량번호':
            df_existing.rename(columns={car_col: '차량번호'}, inplace=True)
        
        # 필요한 컬럼 추가
        if '상태' not in df_existing.columns:
            df_existing['상태'] = '미등록'
        if '처리시간' not in df_existing.columns:
            df_existing['처리시간'] = ''
        if '회차' not in df_existing.columns:
            df_existing['회차'] = ''
        if '데이터소스' not in df_existing.columns:
            df_existing['데이터소스'] = '주차 명단'
        if '등록요청시간' not in df_existing.columns:
            df_existing['등록요청시간'] = ''
        
        # 새 데이터 생성
        new_rows = []
        for car_data in car_data_list:
            # 중복 체크 (같은 차량번호가 없으면 추가)
            car_num = car_data.get('차량번호', '')
            if car_num:
                # 기존 데이터에 같은 차량번호 있는지 확인
                existing = df_existing[df_existing['차량번호'].astype(str).str.replace(' ', '') == car_num.replace(' ', '')]
                if len(existing) > 0:
                    print(f"⚠️ 중복: {car_num} 이미 존재")
                    error_count += 1
                    continue
                
                new_row = {
                    '이름': car_data.get('성함', '미입력'),
                    '차량번호': car_num,
                    '상태': '미등록',
                    '처리시간': '',
                    '회차': '',
                    '데이터소스': '일일 등록',
                    '등록요청시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                new_rows.append(new_row)
                success_count += 1
        
        if new_rows:
            # 새 데이터를 DataFrame으로
            df_new = pd.DataFrame(new_rows)
            
            # 기존 데이터의 컬럼에 맞춤
            for col in df_existing.columns:
                if col not in df_new.columns:
                    df_new[col] = ''
            
            # 순서 맞추기
            df_new = df_new.reindex(columns=df_existing.columns, fill_value='')
            
            # 새 데이터를 맨 위에 추가 (prepend)
            df_combined = pd.concat([df_new, df_existing], ignore_index=True)
            
            # 파일 저장 (재시도 로직)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    df_combined.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    print(f"✅ {success_count}대 CSV 최상단에 추가됨: {os.path.basename(csv_path)}")
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        print(f"⚠️ 파일 접근 대기 중... ({attempt+1}/{max_retries})")
                        time.sleep(1)
                    else:
                        print(f"❌ 파일 저장 실패: 파일이 사용 중입니다")
                        return (0, len(car_data_list))
        
        return (success_count, error_count)
        
    except Exception as e:
        print(f"❌ CSV 처리 오류: {e}")
        return (0, len(car_data_list))


def get_pending_cars(csv_path: str = None, priority_first: bool = True) -> pd.DataFrame:
    """
    미등록 차량 목록 조회 (우선순위순)
    
    Args:
        csv_path: 대상 CSV 파일
        priority_first: True면 일일 등록 먼저 (기본값)
    
    Returns:
        미등록 차량 DataFrame
    """
    if not csv_path:
        csv_path = get_latest_db_file()
    
    if not csv_path or not os.path.exists(csv_path):
        return None
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        
        # 미등록만 필터
        if '상태' in df.columns:
            df = df[df['상태'].isin(['미등록', '', pd.NA]) | df['상태'].isna()].copy()
        
        # 우선순위 정렬: 일일 등록 먼저
        if priority_first and '데이터소스' in df.columns:
            # 일일 등록 = 0, 주차 명단 = 1
            df['_priority'] = df['데이터소스'].apply(
                lambda x: 0 if x == '일일 등록' else 1
            )
            df = df.sort_values('_priority').drop(columns=['_priority'])
        
        return df
        
    except Exception as e:
        print(f"❌ CSV 읽기 오류: {e}")
        return None
