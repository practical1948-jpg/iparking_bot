# 크롬 브라우저에서 멤버스 상점 할인 적용 자동화 스크립트
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_temp"
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import re
import time
import subprocess
import os
import socket
import csv
import pandas as pd
from pathlib import Path
import glob
import json
import threading  # 신규 일일 등록 감지용
from firebase_helper import save_parking_record, initialize_firebase, check_record_exists, check_record_exists_by_car, get_existing_record_by_car, clean_today_orphaned_records, get_processed_cars_today, update_bot_heartbeat


# ========================================
# 🚨 신규 일일 등록 감지 시스템
# ========================================
NEW_DAILY_DETECTED = False  # 신규 일일 등록 감지 플래그
LAST_DAILY_CHECK_TIME = None  # 마지막 체크 시간
DETECTION_LOCK = threading.Lock()  # 스레드 안전성



# 계정 정보
ACCOUNTS = [
    {"username": "dreamcb01", "password": "dreamcb01"},
    {"username": "dreamcb02", "password": "dreamcb02"},
    {"username": "dreamcb03", "password": "dreamcb03"}
]

# 주차 DB 파일 전용 폴더 경로 (상대 경로 사용 - 배포 가능)
# 현재 스크립트 파일의 위치를 기준으로 상위 디렉토리 사용
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # iparking-bot 폴더의 상위 디렉토리
DB_FOLDER = os.path.join(BASE_DIR, "주차_DB_파일")
EXECUTION_LOG_PATH = os.path.join(BASE_DIR, "file_execution_log.json")

# 주차 DB 폴더 생성 (없으면)
os.makedirs(DB_FOLDER, exist_ok=True)

# 로그 폴더 생성
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
BOT_LOG_PATH = os.path.join(LOGS_DIR, f"bot_{datetime.now().strftime('%Y%m%d')}.log")

def log_to_file(message, level="INFO"):
    """콘솔 출력과 동시에 파일에 로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_msg = f"[{timestamp}] [{level}] {message}"
    print(formatted_msg)
    try:
        with open(BOT_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"⚠️ 로그 파일 기록 실패: {e}")

def get_current_round():
    """오늘 날짜 기준 실행 회차 결정"""
    try:
        if os.path.exists(EXECUTION_LOG_PATH):
            with open(EXECUTION_LOG_PATH, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        else:
            return 1
        
        # 오늘 날짜
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 오늘 실행 기록 카운트 (실행 이력 리스트에서 오늘 날짜인 것만 카운트)
        today_count = 0
        for execution in log_data.get("execution_list", []):
            exec_time = execution.get("executed_at", "")
            if exec_time.startswith(today):
                today_count += 1
        
        return today_count + 1  # 다음 회차
    except Exception as e:
        print(f"회차 계산 오류: {e}")
        return 1

def log_file_execution(file_path):
    """파일 실행 이력을 로그에 기록"""
    try:
        # 로그 파일 읽기
        if os.path.exists(EXECUTION_LOG_PATH):
            with open(EXECUTION_LOG_PATH, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        else:
            log_data = {
                "execution_history": {},  # 파일별 요약 정보 (호환성 유지)
                "execution_list": []       # 실행 이력 리스트 (회차 계산용)
            }
        
        # execution_list가 없으면 추가 (기존 로그 호환)
        if "execution_list" not in log_data:
            log_data["execution_list"] = []
        
        # 실행 기록 추가
        file_name = os.path.basename(file_path)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. 실행 이력 리스트에 추가 (회차 계산용)
        log_data["execution_list"].append({
            "file_name": file_name,
            "file_path": file_path,
            "executed_at": current_time
        })
        
        # 2. 파일별 요약 정보 업데이트 (호환성 유지)
        if "execution_history" not in log_data:
            log_data["execution_history"] = {}
            
        if file_name not in log_data["execution_history"]:
            log_data["execution_history"][file_name] = {
                "last_executed": current_time,
                "execution_count": 1,
                "file_path": file_path
            }
        else:
            log_data["execution_history"][file_name]["last_executed"] = current_time
            log_data["execution_history"][file_name]["execution_count"] += 1
            log_data["execution_history"][file_name]["file_path"] = file_path
        
        # 로그 저장
        with open(EXECUTION_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"📝 파일 실행 기록: {file_name}")
    except Exception as e:
        print(f"⚠️ 로그 기록 실패: {e}")

def auto_push_to_github():
    """봇 실행 결과를 자동으로 GitHub에 푸시"""
    try:
        print("\n" + "="*60)
        print("📤 GitHub 자동 업로드 시작")
        print("="*60)
        
        # 프로젝트 루트 디렉토리로 이동
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)
        
        # Git 상태 확인
        result = subprocess.run(['git', 'status', '--short'], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if not result.stdout.strip():
            print("  ℹ️  변경사항 없음 - 업로드 건너뛰기")
            return True
        
        print(f"  📝 변경된 파일:\n{result.stdout}")
        
        # Git add
        print("  1️⃣ 파일 추가 중...")
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Git commit
        print("  2️⃣ 커밋 중...")
        commit_msg = f"Update parking data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Git push
        print("  3️⃣ GitHub에 업로드 중...")
        subprocess.run(['git', 'push'], check=True)
        
        print("\n✅ GitHub 업로드 완료!")
        print("="*60 + "\n")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Git 명령 실패: {e}")
        print("수동으로 git push를 실행해주세요.")
        return False
    except Exception as e:
        print(f"\n⚠️ GitHub 업로드 실패: {e}")
        return False

def get_latest_db_file():
    """주차_DB_파일 폴더에서 가장 최근 CSV 파일을 찾음"""
    try:
        # 폴더 내 모든 CSV 파일 검색
        csv_files = glob.glob(os.path.join(DB_FOLDER, "*.csv"))
        
        if not csv_files:
            return None
        
        # 수정 시간 기준으로 정렬 (최신 순)
        latest_file = max(csv_files, key=os.path.getmtime)
        return latest_file
    except Exception as e:
        print(f"최신 파일 검색 오류: {e}")
        return None

# CSV 파일 경로 옵션 (기본 경로, 파일이 없으면 선택 가능)
CSV_FILES = {
    "1": {
        "name": "차량_DB (대량 등록용)",
        "path": get_latest_db_file() or "",  # 상대 경로 사용 - 기본값은 빈 문자열
        "default_dir": DB_FOLDER  # 주차_DB_파일 폴더를 기본으로
    }
}

def select_csv_file(default_path="", default_dir=""):
    """파일 선택 대화상자로 CSV 파일 선택"""
    try:
        from tkinter import Tk, filedialog
        
        # Tkinter 루트 윈도우 생성 (숨김)
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        print("\n파일 선택 대화상자가 열립니다...")
        
        # 파일 선택 대화상자
        file_path = filedialog.askopenfilename(
            title="CSV 파일을 선택하세요",
            initialdir=default_dir if default_dir else os.path.dirname(default_path) if default_path else os.getcwd(),
            filetypes=[
                ("CSV 파일", "*.csv"),
                ("모든 파일", "*.*")
            ]
        )
        
        root.destroy()
        
        if file_path:
            print(f"선택된 파일: {file_path}")
            return file_path
        else:
            print("파일 선택이 취소되었습니다.")
            return None
            
    except ImportError:
        print("⚠️ tkinter를 사용할 수 없습니다. 수동으로 경로를 입력하세요.")
        file_path = input("CSV 파일 전체 경로를 입력하세요: ").strip().strip('"')
        if os.path.exists(file_path):
            return file_path
        else:
            print("파일을 찾을 수 없습니다.")
            return None
    except Exception as e:
        print(f"파일 선택 오류: {e}")
        return None

# 선택된 CSV 파일 경로 (프로그램 시작 시 설정됨)
CSV_FILE_PATH = None

# 데이터 입력 모드 ('csv' 또는 'manual')
INPUT_MODE = None

# 수동 입력 데이터 저장
MANUAL_DATA = []

# iParking 로그인 함수
def login_to_iparking(driver, username, password):
    """iParking 사이트에 로그인"""
    wait = WebDriverWait(driver, 10)
    try:
        # 아이디 입력
        id_input = wait.until(EC.presence_of_element_located((By.ID, "id")))
        id_input.clear()
        id_input.send_keys(username)
        
        # 비밀번호 입력
        pw_input = driver.find_element(By.ID, "password")
        pw_input.clear()
        pw_input.send_keys(password)
        
        # 로그인 버튼 클릭 (여러 가능한 선택자 시도)
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_btn.click()
        except:
            try:
                login_btn = driver.find_element(By.XPATH, "//button[contains(text(), '로그인')]")
                login_btn.click()
            except:
                # Enter 키로 로그인 시도
                pw_input.send_keys('\n')
        
        time.sleep(2)
        return True
    except Exception as e:
        print(f"    로그인 실패: {e}")
        return False

# 차량번호 정규화 함수 (한글, 숫자만 남김)
def normalize_car_number(car_number):
    return re.sub(r'[^가-힣0-9]', '', car_number)

# 수동 입력은 Firebase에만 저장 (CSV 파일 불필요)
def save_manual_input_to_csv():
    """수동 입력 데이터는 Firebase에만 저장됩니다 (호환성 유지용 빈 함수)"""
    global MANUAL_DATA
    
    if not MANUAL_DATA:
        return
    
    # Firebase에만 저장하므로 별도 처리 불필요
    print(f"수동 입력 데이터 준비 완료: {len(MANUAL_DATA)}개 (Firebase에 저장됨)")

# 수동 입력 받기 함수
def get_manual_input():
    """수동으로 차량 정보 입력받기"""
    global MANUAL_DATA
    
    print("\n차량 정보를 입력하세요")
    print("형식: 차량번호만 또는 이름 차량번호 (공백 구분)")
    print("예시: 42서4631          (차량번호만)")
    print("      정세윤 42서4631   (이름 차량번호)")
    print("      19두0353         (공백 없이 붙여서)")
    print("여러 줄 입력 가능, 입력 완료 후 빈 줄에서 Enter 누르기")
    print("(종료하려면 'q' 또는 'quit' 입력)")
    print("-" * 60)
    
    MANUAL_DATA.clear()
    line_count = 0
    
    while True:
        line = input().strip()
        if not line:  # 빈 줄이면 입력 종료
            break
        
        # 종료 명령어 체크
        if line.lower() in ['q', 'quit', 'exit', '종료']:
            return False  # 종료 신호
        
        # 공백이나 탭으로 구분
        parts = line.split()
        
        if len(parts) == 1:
            # 차량번호만 입력한 경우
            car_number = parts[0]
            # 차량번호 길이 체크 (최소 6자 이상 권장)
            if len(normalize_car_number(car_number)) < 5:
                print(f"  ⚠️ 경고: '{car_number}' - 차량번호가 너무 짧습니다 (5자 미만)")
                print(f"      전체 차량번호를 입력하세요 (예: 19두0353)")
                continue
            name = ""
            MANUAL_DATA.append([name, car_number])
            line_count += 1
            print(f"  ✓ {line_count}. {car_number}")
        elif len(parts) >= 2:
            # 첫 단어가 한글로만 되어있으면 → 이름, 아니면 → 차량번호 일부
            first_word = parts[0]
            if re.match(r'^[가-힣]+$', first_word):
                # 순수 한글 → 이름으로 인식
                name = first_word
                car_number = ''.join(parts[1:])  # 나머지는 모두 차량번호 (공백 제거)
                # 차량번호 길이 체크
                if len(normalize_car_number(car_number)) < 5:
                    print(f"  ⚠️ 경고: '{name} {car_number}' - 차량번호가 너무 짧습니다 (5자 미만)")
                    print(f"      전체 차량번호를 입력하세요 (예: {name} 19두0353)")
                    continue
                MANUAL_DATA.append([name, car_number])
                line_count += 1
                print(f"  ✓ {line_count}. {name} - {car_number}")
            else:
                # 한글+숫자 섞임 → 전체를 차량번호로 (공백 제거)
                car_number = ''.join(parts)
                name = ""
                # 차량번호 길이 체크
                if len(normalize_car_number(car_number)) < 5:
                    print(f"  ⚠️ 경고: '{car_number}' - 차량번호가 너무 짧습니다 (5자 미만)")
                    print(f"      전체 차량번호를 입력하세요 (예: 19두0353)")
                    continue
                MANUAL_DATA.append([name, car_number])
                line_count += 1
                print(f"  ✓ {line_count}. {car_number}")
        else:
            print(f"  ✗ 잘못된 형식입니다. 다시 입력하세요.")
    
    if len(MANUAL_DATA) == 0:
        return None  # 입력 없음
    
    print(f"\n총 {len(MANUAL_DATA)}개 차량 입력 완료")
    return True  # 입력 완료

# 수동 입력 데이터 읽기
def read_manual_input():
    """수동으로 입력된 차량 정보를 DataFrame으로 변환"""
    global MANUAL_DATA
    
    if not MANUAL_DATA:
        return None
    
    # DataFrame 생성
    df = pd.DataFrame(MANUAL_DATA, columns=['이름', '차량번호'])
    df['상태'] = '미등록'
    df['처리시간'] = pd.Series(dtype='object')  # 문자열 타입으로 명시
    
    return df

# CSV 파일에서 차량 정보 읽기
def read_car_data_from_csv():
    """CSV 파일에서 차량번호 및 상태 정보 읽기 (우선순위 정렬 포함)"""
    try:
        # CSV 파일 읽기 (헤더가 2줄인 경우 처리)
        df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig')
        
        # 첫 번째 행이 예시인 경우 제거 (예시) 103가3456 같은 텍스트 포함)
        if len(df) > 0 and '예시' in str(df.iloc[0].values):
            df = df.iloc[1:].reset_index(drop=True)
        
        # 열 이름 정규화 (줄바꿈 제거)
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        
        # 차량번호 열 찾기 (다양한 이름 지원)
        car_number_col = None
        for col in df.columns:
            if '차량번호' in col or '차량' in col:
                car_number_col = col
                break
        
        if car_number_col:
            df.rename(columns={car_number_col: '차량번호'}, inplace=True)
        
        # 필수 컬럼 추가 (없으면)
        if '상태' not in df.columns:
            df['상태'] = '미등록'
        if '처리시간' not in df.columns:
            df['처리시간'] = pd.Series(dtype='object')
        if '회차' not in df.columns:
            df['회차'] = pd.Series(dtype='object')
        if '데이터소스' not in df.columns:
            df['데이터소스'] = '주차 명단'
        
        # ========================================
        # 🚀 우선순위 정렬: 일일 등록 먼저 처리!
        # ========================================
        # 정렬 전 원본 인덱스 저장 (업데이트 시 위치 추적용)
        df['original_index'] = df.index
        
        # 일일 등록 = 0 (먼저), 주차 명단 = 1 (나중)
        df['_priority'] = df['데이터소스'].apply(
            lambda x: 0 if str(x) == '일일 등록' else 1
        )
        df = df.sort_values('_priority').drop(columns=['_priority']).reset_index(drop=True)
        
        # 미등록만 필터링 (이미 처리된 차량 제외)
        pending_mask = df['상태'].isin(['미등록', '']) | df['상태'].isna()
        pending_count = pending_mask.sum()
        total_count = len(df)
        
        print(f"✅ CSV 로드 완료 - 전체 {total_count}대, 미등록 {pending_count}대")
        print(f"   📌 우선순위 정렬 완료 (일일 등록 → 주차 명단)")
        print(f"   📌 원본 인덱스 보존 완료 (순서가 바뀌어도 정확한 위치 업데이트)")
        
        return df
    except Exception as e:
        print(f"CSV 파일 읽기 실패: {e}")
        return None

# CSV 파일 업데이트
def update_csv_status(index, status, timestamp=None, car_number=None, round_num=None):
    """CSV 파일의 특정 행 상태 업데이트 + Firebase 동기화"""
    # 수동 입력 모드면 Firebase에만 저장 (CSV 불필요)
    if INPUT_MODE == 'manual':
        # Firebase에만 동기화
        firebase_data = {
            '회차': '',
            '번호': int(index) + 1,
            '성함': '',  # 수동 입력에는 이름이 있을 수 있음
            '차량번호': car_number or '',
            '상태': status,
            '처리시간': timestamp or '',
            '데이터소스': '일일 등록'
        }
        save_parking_record(firebase_data)
        return True
    
    csv_path = CSV_FILE_PATH
    
    if not csv_path:
        return True
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 열 이름 정규화
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        
        # 차량번호 열 찾기
        car_number_col = None
        for col in df.columns:
            if '차량번호' in col or '차량' in col:
                car_number_col = col
                break
        if car_number_col:
            df.rename(columns={car_number_col: '차량번호'}, inplace=True)
        
        # 상태, 처리시간, 회차 열이 없으면 추가
        if '상태' not in df.columns:
            df['상태'] = '미등록'
        if '처리시간' not in df.columns:
            df['처리시간'] = pd.Series(dtype='object')  # 문자열 타입으로 명시
        if '회차' not in df.columns:
            df['회차'] = pd.Series(dtype='object')      # 문자열 타입으로 명시
        
        # 수동 입력 모드면 차량번호로 찾기
        if INPUT_MODE == 'manual' and car_number:
            # 차량번호로 행 찾기
            car_normalized = normalize_car_number(car_number)
            mask = df['차량번호'].apply(lambda x: normalize_car_number(str(x)) == car_normalized)
            if mask.any():
                df.loc[mask, '상태'] = str(status)
                if timestamp:
                    df.loc[mask, '처리시간'] = str(timestamp)  # 명시적 문자열 변환
                # 일일 등록은 회차 기록 안함
                
                # Firebase 동기화
                row_data = df[mask].iloc[0]
                firebase_data = {
                    '회차': '',
                    '번호': int(row_data.name) + 1,
                    '성함': str(row_data.get('이름', '')),
                    '차량번호': car_number,
                    '상태': status,
                    '처리시간': timestamp or '',
                    '데이터소스': '일일 등록'
                }
                save_parking_record(firebase_data)
            else:
                print(f"  경고: 차량번호 {car_number}를 CSV에서 찾을 수 없습니다.")
        else:
            # 일반 모드: 인덱스로 업데이트
            df.loc[index, '상태'] = str(status)
            if timestamp:
                df.loc[index, '처리시간'] = str(timestamp)  # 명시적 문자열 변환
            if round_num and INPUT_MODE == 'csv':  # CSV 모드만 회차 기록
                df.loc[index, '회차'] = str(round_num)      # 명시적 문자열 변환
            
            # Firebase 동기화 (CSV 모드만)
            if INPUT_MODE == 'csv':
                row_data = df.loc[index]
                firebase_data = {
                    '회차': int(round_num) if round_num else '',
                    '번호': int(index) + 1,
                    '성함': str(row_data.get('이름', '')),
                    '차량번호': car_number or str(row_data.get('차량번호', '')),
                    '상태': status,
                    '처리시간': timestamp or '',
                    '데이터소스': '주차 명단'
                }
                save_parking_record(firebase_data)
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"CSV 업데이트 실패: {e}")
        return False

# 세션 복구 함수
def recover_session(driver, handles):
    """세션 만료 시 자동으로 재로그인 및 복구"""
    print("\n" + "="*60)
    print("🔄 세션 자동 복구 시작")
    print("="*60)
    
    # 모든 탭 새로고침 및 재로그인
    print("\n모든 탭을 새로고침하고 재로그인합니다...")
    success_count = 0
    
    for idx, handle in enumerate(handles[:3]):  # 3개 계정 탭만
        try:
            driver.switch_to.window(handle)
            
            # 새로고침
            print(f"\n  [{idx+1}/3] 탭 {idx+1} 처리 중...")
            driver.refresh()
            time.sleep(2)
            
            # 현재 URL 확인
            current_url = driver.current_url
            
            # 로그인 페이지인 경우에만 로그인
            if 'login' in current_url:
                print(f"    로그인 페이지 감지 - {ACCOUNTS[idx]['username']} 로그인 중...")
                if login_to_iparking(driver, ACCOUNTS[idx]['username'], ACCOUNTS[idx]['password']):
                    time.sleep(2)
                    if 'login' not in driver.current_url:
                        print(f"    ✅ 로그인 성공!")
                        
                        # 주차비 할인 메뉴로 이동
                        try:
                            discount_url = "http://members.iparking.co.kr/html/discount/carDiscount.html"
                            driver.get(discount_url)
                            time.sleep(2)
                            print(f"    ✅ 주차비 할인 메뉴 이동 완료")
                            success_count += 1
                        except Exception as e:
                            print(f"    ⚠️ 메뉴 이동 실패: {e}")
                    else:
                        print(f"    ❌ 로그인 실패")
                else:
                    print(f"    ❌ 로그인 실패")
            else:
                # 이미 로그인된 경우
                print(f"    ✅ 이미 로그인됨 - 주차비 할인 메뉴로 이동")
                try:
                    discount_url = "http://members.iparking.co.kr/html/discount/carDiscount.html"
                    driver.get(discount_url)
                    time.sleep(2)
                    success_count += 1
                except Exception as e:
                    print(f"    ⚠️ 메뉴 이동 실패: {e}")
                    
        except Exception as e:
            print(f"    ❌ 탭 {idx+1} 복구 실패: {e}")
    
    print("\n" + "="*60)
    print(f"✅ 세션 복구 완료: {success_count}/3개 탭 성공")
    print("="*60 + "\n")
    
    if success_count == 0:
        print("⚠️ 모든 탭 복구 실패! 수동으로 확인이 필요합니다.")
        input("탭들을 확인하고 준비되면 Enter를 눌러주세요...")
    
    return success_count > 0

# HTML 팝업 감지 함수
def check_html_popup(driver, wait):
    """HTML 팝업 감지 및 처리 (세션 만료 등)"""
    try:
        # 여러 가능한 팝업 선택자 시도
        popup_selectors = [
            (By.ID, "popMessage"),  # 일반 팝업
            (By.CSS_SELECTOR, ".popup-message"),  # 클래스 기반
            (By.CSS_SELECTOR, "[class*='popup']"),  # popup 포함 클래스
            (By.CSS_SELECTOR, "[class*='modal']"),  # modal 포함 클래스
        ]
        
        popup_element = None
        popup_text = ""
        
        for selector_type, selector_value in popup_selectors:
            try:
                elements = driver.find_elements(selector_type, selector_value)
                for elem in elements:
                    # 팝업이 보이는지 확인 (display: none이 아닌지)
                    if elem.is_displayed():
                        popup_text = elem.text.strip()
                        if popup_text:  # 텍스트가 있으면
                            popup_element = elem
                            break
                if popup_element:
                    break
            except:
                continue
        
        # 팝업 텍스트 확인
        if popup_text:
            print(f"  ⚠️ [HTML 팝업 감지] {popup_text}")
            
            # 세션 만료 관련 키워드 체크
            session_keywords = ['잘못된 접근', '로그인으로 이동', '로그인', '세션', '만료', '인증', '접근', '재로그인']
            if any(keyword in popup_text for keyword in session_keywords):
                print(f"  ❌ 세션 만료 감지! (팝업: {popup_text})")
                
                # 확인 버튼 찾아서 클릭
                try:
                    # 여러 가능한 확인 버튼 선택자
                    ok_selectors = [
                        (By.ID, "popupOk"),
                        (By.CSS_SELECTOR, "button[class*='ok']"),
                        (By.XPATH, "//button[contains(text(), '확인')]"),
                        (By.XPATH, "//button[contains(text(), 'OK')]"),
                        (By.XPATH, "//button[normalize-space(text())='확인']"),
                    ]
                    
                    clicked = False
                    for sel_type, sel_value in ok_selectors:
                        try:
                            if sel_type == By.XPATH:
                                ok_btn = driver.find_element(sel_type, sel_value)
                            else:
                                ok_btn = driver.find_element(sel_type, sel_value)
                            
                            if ok_btn.is_displayed():
                                ok_btn.click()
                                clicked = True
                                print(f"    확인 버튼 클릭 완료")
                                break
                        except:
                            continue
                    
                    if not clicked:
                        print(f"    ⚠️ 확인 버튼을 찾을 수 없음")
                except Exception as e:
                    print(f"    ⚠️ 확인 버튼 클릭 실패: {e}")
                
                return "session_expired"
        
        return None
    except Exception as e:
        # 팝업이 없으면 정상
        return None

# Alert/팝업 감지 함수
def check_and_handle_alert(driver):
    """Alert 팝업 감지 및 처리"""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"  ⚠️ [Alert 감지] {alert_text}")
        
        # 세션 만료 관련 키워드 체크
        if any(keyword in alert_text for keyword in ['로그인', '세션', '만료', '인증', '접근']):
            print(f"  ❌ 세션 만료 감지! 프로그램을 중단합니다.")
            alert.accept()
            return "session_expired"
        
        alert.accept()
        return "alert_handled"
    except:
        return None

# 차량번호 정규화 함수 (공백, 특수문자 제거, 한글/숫자만)
def normalize_car_number(car_number):
    """차량번호를 정규화 (공백, 하이픈 등 제거)"""
    if not car_number:
        return ""
    return re.sub(r'[^가-힣0-9]', '', str(car_number))

# 주차권(할인권) 적용 함수
def apply_discount(driver, car_number_full, return_home=True):
    """
    주차권 등록 함수
    return_home=False이면 등록 후 홈으로 돌아가지 않음 (할인 내역 화면 유지)
    """
    wait = WebDriverWait(driver, 3)
    
    # Alert 체크
    alert_result = check_and_handle_alert(driver)
    if alert_result == "session_expired":
        return "session_expired"
    
    # HTML 팝업 체크 (세션 만료 등)
    popup_result = check_html_popup(driver, wait)
    if popup_result == "session_expired":
        return "session_expired"
    
    try:
        input_box = wait.until(EC.element_to_be_clickable((By.ID, "carNumber")))
        input_box.clear()
        last4 = car_number_full[-4:]
        input_box.send_keys(last4)
        driver.find_element(By.CLASS_NAME, "btn-search").click()
        
        # 검색 후 다시 Alert 체크
        time.sleep(0.5)
        alert_result = check_and_handle_alert(driver)
        if alert_result == "session_expired":
            return "session_expired"
        
        # 검색 후 HTML 팝업 체크
        popup_result = check_html_popup(driver, wait)
        if popup_result == "session_expired":
            return "session_expired"
        
        # 검색 후 다시 Alert 체크
        time.sleep(0.5)
        alert_result = check_and_handle_alert(driver)
        if alert_result == "session_expired":
            return "session_expired"
        
        # 검색 후 HTML 팝업 체크
        popup_result = check_html_popup(driver, wait)
        if popup_result == "session_expired":
            return "session_expired"
        
        # 차량 없음 메시지 확인 (더 확실하게)
        try:
            # parkName 요소가 있고, 그 안에 "검색된 차량이 없습니다" 텍스트가 명확히 있을 때만
            no_result = wait.until(EC.visibility_of_element_located((By.ID, "parkName")))
            no_result_text = no_result.text.strip()
            
            if "검색된 차량이 없습니다" in no_result_text:
                print(f"    🚫 '차량 없음' 메시지 감지됨: {no_result_text}")
                try:
                    home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                    home_btn_right.click()
                except Exception:
                    pass
                return "no_car"
        except Exception:
            # parkName이 없거나 텍스트가 다르면 결과가 있을 수 있으므로 계속 진행
            pass
            
        # 결과 테이블 로딩 대기 (최대 2초)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".car-number-cell, td")))
        except:
            pass # 못 찾아도 아래에서 find_elements로 재확인
            
        results = driver.find_elements(By.CSS_SELECTOR, ".car-number-cell")
        
        # 만약 .car-number-cell로 못 찾으면 일반 td 태그로도 시도
        if len(results) == 0:
            results = driver.find_elements(By.TAG_NAME, "td")
        
        search_number = normalize_car_number(car_number_full)
        found = False
        partial_matches = []  # 뒷 4자리만 일치하는 경우들
        
        for result in results:
            td_number = normalize_car_number(result.text)
            if td_number == search_number:
                # 전체 번호 완전 일치
                result.click()
                found = True
                break
            elif len(search_number) >= 4 and td_number[-4:] == search_number[-4:]:
                # 뒷 4자리만 일치
                partial_matches.append((result, td_number))
        
        if not found:
            # 전체 일치하는 게 없을 때
            if len(partial_matches) == 1:
                # 검색 결과가 정확히 1개 → 자동 클릭
                partial_matches[0][0].click()
                found = True
                print(f"    ℹ️ 뒷 4자리 일치 차량 1개 발견 → 자동 선택: {partial_matches[0][1]}")
            elif len(partial_matches) > 1:
                # 2개 이상 → 경고
                print(f"    ⚠️ 뒷 4자리 일치 차량 {len(partial_matches)}개 발견 → 전체 번호 필요")
                print(f"       발견된 차량: {', '.join([m[1] for m in partial_matches])}")
                try:
                    home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                    home_btn_right.click()
                except Exception:
                    pass
                return "error_multiple"
            else:
                # 뒷 4자리도 안 맞음
                print(f"    ℹ️ 검색된 차량 번호가 일치하지 않음 (화면 목록에서 찾을 수 없음)")
                print(f"       - 검색 대상: {search_number}")
                print(f"       - 화면 목록: {', '.join([normalize_car_number(r.text) for r in results])}")
                try:
                    home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                    home_btn_right.click()
                except Exception:
                    pass
                return "no_car"
        
        # found == True인 경우 계속 진행
        select_btn = wait.until(EC.element_to_be_clickable((By.ID, "next")))
        select_btn.click()
        apply_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-apply")))
        apply_btn.click()
        
        # 팝업 처리 (단순하게)
        # 먼저 세션 만료 팝업 체크
        popup_result = check_html_popup(driver, wait)
        if popup_result == "session_expired":
            return "session_expired"
        
        try:
            ok_btn = wait.until(EC.element_to_be_clickable((By.ID, "popupOk")))
            ok_btn.click()
            ok_btn2 = wait.until(EC.element_to_be_clickable((By.ID, "popupOk")))
            ok_btn2.click()
        except Exception:
            pass
            
        # 홈으로 돌아가기 (return_home=True일 때만)
        if return_home:
            try:
                home_btn = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                home_btn.click()
            except Exception:
                pass
        
        return "success"
    except Exception as e:
        # 예외 상황 분석
        error_msg = str(e).lower()
        
        # TimeoutException: 요소를 못 찾은 경우 (세션 만료 가능성)
        if "timeout" in error_msg or "element" in error_msg:
            # Alert 다시 한번 체크
            alert_result = check_and_handle_alert(driver)
            if alert_result == "session_expired":
                return "session_expired"
            
            # HTML 팝업 체크
            popup_result = check_html_popup(driver, wait)
            if popup_result == "session_expired":
                return "session_expired"
            
            # Alert 없으면 요소 찾기 실패 = 페이지 구조 문제
            print(f"    [요소 찾기 실패] {e}")
            try:
                home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                home_btn_right.click()
            except Exception:
                pass
            return "no_car"
        
        # 기타 예외
        # HTML 팝업 체크
        popup_result = check_html_popup(driver, wait)
        if popup_result == "session_expired":
            return "session_expired"
        
        try:
            home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
            home_btn_right.click()
        except Exception:
            pass
        return "error"

# 적용된 할인권 개수 확인 함수
def check_applied_discounts(driver, wait):
    """
    '총 할인 내역 및 적용 수량' 이후에 나오는 <td>1시간(무료)</td> 개수를 확인
    정확한 선택자로 추정 없이 실제 개수만 카운트
    """
    try:
        time.sleep(3)  # 페이지 로딩 대기
        
        # "총 할인 내역 및 적용 수량" <p> 태그 이후에 나오는 <td>1시간(무료)</td> 찾기
        try:
            discount_items = driver.find_elements(By.XPATH, "//p[contains(text(), '총 할인 내역')]/following::td[text()='1시간(무료)']")
            discount_count = len(discount_items)
            
            if discount_count > 0:
                print(f"    [할인권 감지 ✓] '총 할인 내역' 이후 <td>1시간(무료)</td> {discount_count}개 발견")
            else:
                print(f"    [할인권 감지 ✗] <td>1시간(무료)</td> 요소를 찾을 수 없음")
            
            return discount_count
            
        except Exception as e:
            print(f"    [할인권 감지 오류] {e}")
            return 0
        
    except Exception as e:
        print(f"    [할인권 확인 오류] {e}")
        return 0

# ========================================
# 🚨 신규 일일 등록 감지 백그라운드 스레드
# ========================================
def check_new_daily_background():
    """
    백그라운드 스레드: 5분마다 신규 일일 등록 체크
    신규 감지 시 NEW_DAILY_DETECTED 플래그 설정
    """
    global NEW_DAILY_DETECTED, LAST_DAILY_CHECK_TIME
    
    print("🔍 [백그라운드] 신규 일일 등록 감지 스레드 시작")
    
    while True:
        try:
            time.sleep(300)  # 5분 대기
            
            if not CSV_FILE_PATH or not os.path.exists(CSV_FILE_PATH):
                continue
            
            # CSV 재로드
            df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig')
            df.columns = df.columns.str.replace('\n', ' ').str.strip()
            
            # 데이터소스 컬럼 확인
            if '데이터소스' not in df.columns:
                continue
            
            # 일일 등록만 필터
            daily_df = df[df['데이터소스'] == '일일 등록'].copy()
            
            if len(daily_df) == 0:
                continue
            
            # 등록요청시간 컬럼 확인
            if '등록요청시간' not in daily_df.columns:
                continue
            
            # 마지막 체크 이후 신규 데이터 확인
            if LAST_DAILY_CHECK_TIME is None:
                # 첫 실행: 현재 시간 저장만
                with DETECTION_LOCK:
                    LAST_DAILY_CHECK_TIME = datetime.now()
                print(f"🔍 [백그라운드] 초기화 완료 - 현재 일일 등록: {len(daily_df)}대")
            else:
                # 신규 데이터 확인
                new_daily = daily_df[
                    pd.to_datetime(daily_df['등록요청시간'], errors='coerce') > LAST_DAILY_CHECK_TIME
                ]
                
                if len(new_daily) > 0:
                    with DETECTION_LOCK:
                        NEW_DAILY_DETECTED = True
                        LAST_DAILY_CHECK_TIME = datetime.now()
                    
                    print(f"\n🚨 [백그라운드] ★★★ 신규 일일 차량 {len(new_daily)}대 감지! ★★★")
                    print(f"   → 현재 처리 완료 후 처음부터 재시작합니다.\n")
                    
        except Exception as e:
            print(f"⚠️ [백그라운드] 감지 오류 (무시): {e}")
            continue

def run_parking_automation():
    """주차권 등록 자동화 실행 함수"""
    print(f"\n=== iParking 자동화 실행 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # Firebase 초기화
    print("🔥 Firebase 연결 중...")
    initialize_firebase()
    
    # 현재 회차 결정 (CSV 모드만)
    current_round = None
    if INPUT_MODE == 'csv':
        current_round = get_current_round()
        print(f"🔄 실행 회차: {current_round}")
    
    # 파일 실행 로그 기록
    if CSV_FILE_PATH and os.path.exists(CSV_FILE_PATH):
        log_file_execution(CSV_FILE_PATH)
    
    # 데이터 읽기 (모드에 따라)
    if INPUT_MODE == 'manual':
        print("수동 입력 모드")
        # 수동 입력 데이터를 일일 주차 CSV에 먼저 저장
        save_manual_input_to_csv()
        df = read_manual_input()
        if df is None:
            print("입력된 데이터가 없습니다.")
            return
        print(f"수동 입력 데이터 로드 완료: 총 {len(df)}개 차량")
    else:
        print(f"CSV 파일: {os.path.basename(CSV_FILE_PATH)}")
        df = read_car_data_from_csv()
        if df is None:
            print("CSV 파일을 읽을 수 없습니다.")
            return
        print(f"CSV 파일 로드 완료: 총 {len(df)}개 차량")
        
        # Firebase 고아 데이터 정리는 하지 않음 (이전 회차 데이터 보존)
    
    processed_count = 0  # 실제 처리한 차량 수
    success_count = 0  # 성공한 차량 수
    session_alive = True  # 세션 상태
    
    # ========================================
    # 🚀 Firebase 캐싱: 한 번에 조회하여 메모리에 저장
    # ========================================
    # 기존: 차량마다 Firebase 조회 (123번 조회!)
    # 변경: 시작 시 한 번만 조회 (1번 조회!)
    processed_cars_cache = {}  # 캐시 초기화
    
    if INPUT_MODE == 'csv':
        print("\n📊 Firebase 캐싱 시작...")
        data_source = '주차 명단'
        processed_cars_cache = get_processed_cars_today(data_source)
        print(f"📊 캐싱 완료! 이후 중복 체크는 메모리에서 O(1)로 수행됩니다.\n")
    
    for idx, row in df.iterrows():
        car_number_raw = str(row['차량번호']).strip()
        current_status = str(row['상태']).strip()
        
        # 정렬된 상태의 idx가 아닌, 원본 파일의 위치(original_index)를 사용
        # (CSV 모드일 때만 original_index가 존재, 수동 모드는 없음)
        if INPUT_MODE == 'csv' and 'original_index' in row:
            original_idx = int(row['original_index'])
        else:
            original_idx = idx  # 수동 모드 등에서는 그냥 idx 사용
        
        # 이름 정보 가져오기 (있으면)
        name = str(row.get('이름', '')).strip() if '이름' in row else ''
        display_name = f"{name} - " if name and name != 'nan' else ""
        
        # 빈 차량번호는 건너뛰기
        if not car_number_raw or car_number_raw == 'nan':
            continue
        
        # Firebase 중복 체크 (CSV 모드만) - 캐시 기반 O(1) 조회!
        if INPUT_MODE == 'csv':
            # 캐시에서 조회 (Firebase 호출 없이 즉시 확인!)
            cached_status = processed_cars_cache.get(car_number_raw, None)
            
            if cached_status and '등록성공' in cached_status:
                # 등록 성공한 차량만 건너뛰기
                print(f"[{idx+1}/{len(df)}] {display_name}{car_number_raw} - 이미 등록 완료, 건너뛰기")
                continue
            elif cached_status:
                # 실패/차량없음 등은 다시 시도
                print(f"[{idx+1}/{len(df)}] {display_name}{car_number_raw} - 이전 상태: {cached_status}, 재시도")
        else:
            # 수동 입력 모드: 중복 체크 없이 바로 처리
            print(f"[{idx+1}/{len(df)}] {display_name}{car_number_raw} - 수동 입력 (중복 체크 생략)")
        
        # 차량번호 정규화 (공백 제거)
        car_number = normalize_car_number(car_number_raw)
        
        print(f"\n[{idx+1}/{len(df)}] {display_name}{car_number_raw} (정규화: {car_number}) - 주차권 등록 시작")
        processed_count += 1
        
        # 각 탭에서 할인권 적용 시도
        tab_results = []
        last_tab_idx = len(handles) - 1  # 마지막 탭 인덱스
        
        for tab_idx in range(len(handles)):
            try:
                driver.switch_to.window(handles[tab_idx])
                # 올바른 iParking 사이트인지 확인
                current_url = driver.current_url
                if 'iparking' not in current_url.lower():
                    print(f"  {tab_idx+1}번째 탭: 잘못된 사이트 ({current_url}) - 건너뛰기")
                    tab_results.append("skip")
                    continue
                    
                print(f"  {tab_idx+1}번째 탭에서 시도 중...")
                
                # 마지막 탭이면 홈으로 돌아가지 않음 (할인 내역 화면 유지)
                is_last_tab = (tab_idx == last_tab_idx)
                result = apply_discount(driver, car_number, return_home=not is_last_tab)
                
                # 세션 만료 감지
                if result == "session_expired":
                    print(f"  ❌ 세션 만료 감지!")
                    
                    # 자동 복구 시도
                    if recover_session(driver, handles):
                        print("  ✅ 세션 복구 완료! 현재 차량부터 다시 시도합니다.\n")
                        # 처음부터 다시 시도 (현재 차량)
                        tab_results = []
                        for retry_tab_idx in range(len(handles)):
                            try:
                                driver.switch_to.window(handles[retry_tab_idx])
                                print(f"  {retry_tab_idx+1}번째 탭에서 재시도 중...")
                                
                                is_last_tab = (retry_tab_idx == last_tab_idx)
                                retry_result = apply_discount(driver, car_number, return_home=not is_last_tab)
                                
                                tab_results.append(retry_result)
                                print(f"  {retry_tab_idx+1}번째 탭 결과: {retry_result}")
                            except Exception as e:
                                print(f"  {retry_tab_idx+1}번째 탭: 재시도 실패 - {e}")
                                tab_results.append("error")
                    else:
                        print("  ❌ 세션 복구 실패! 작업을 중단합니다.")
                        session_alive = False
                    break
                
                tab_results.append(result)
                print(f"  {tab_idx+1}번째 탭 결과: {result}")
            except Exception as e:
                print(f"  {tab_idx+1}번째 탭: 접근 실패 - {e}")
                tab_results.append("error")
        
        # 세션 만료 시 루프 중단
        if not session_alive:
            print("\n⚠️ 세션 복구에 실패하여 작업을 중단합니다.")
            break
        
        # 마지막 탭에서 할인권 개수 확인 (현재 화면에서 바로)
        print(f"  [총 할인권 확인] {display_name}{car_number_raw} - 적용된 할인권 개수 확인 중...")
        
        wait = WebDriverWait(driver, 3)
        
        try:
            # 마지막 탭이 이미 할인 내역 화면에 있으므로 바로 개수 확인
            discount_count = check_applied_discounts(driver, wait)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 3개 모두 성공해야만 "성공" 처리 (엄격)
            if discount_count == 3:
                print(f"  ✅ {display_name}{car_number_raw} → 주차권 3개 부여됨 (완료)")
                update_csv_status(original_idx, f"등록성공(완료)", timestamp, car_number=car_number_raw, round_num=current_round)
                success_count += 1
            elif discount_count > 0:
                # 1~2개만 적용 = 부분 성공
                print(f"  ⚠️ {display_name}{car_number_raw} → 주차권 {discount_count}개만 부여됨 (부분성공)")
                update_csv_status(original_idx, f"부분성공({discount_count}개)", timestamp, car_number=car_number_raw, round_num=current_round)
            else:
                # 0개 적용
                # tab_results에서 차량 없음 확인
                if any("no_car" in str(r) for r in tab_results):
                    print(f"  ⚠️ {display_name}{car_number_raw} → 차량 없음")
                    update_csv_status(original_idx, "차량 없음", timestamp, car_number=car_number_raw, round_num=current_round)
                else:
                    print(f"  ❌ {display_name}{car_number_raw} → 주차권 0개 (부여 실패)")
                    update_csv_status(original_idx, "실패(0개)", timestamp, car_number=car_number_raw, round_num=current_round)
            
            # 확인 완료 후 홈으로 돌아가기
            try:
                home_btn = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                home_btn.click()
            except Exception:
                pass
                
        except Exception as e:
            print(f"  [총 할인권 확인] {display_name}{car_number_raw} - 확인 중 오류: {e}")
            update_csv_status(original_idx, "실패(오류)", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), car_number=car_number_raw, round_num=current_round)
            try:
                home_btn = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                home_btn.click()
            except Exception:
                pass
        
        # ========================================
        # 🚨 신규 일일 등록 감지 확인
        # ========================================
        # 현재 차량 처리 완료 후 체크
        global NEW_DAILY_DETECTED
        check_flag = False
        with DETECTION_LOCK:
            if NEW_DAILY_DETECTED:
                check_flag = True
                NEW_DAILY_DETECTED = False  # 플래그 리셋
        
        if check_flag:
            print(f"\n{'='*60}")
            print(f"🔄 신규 일일 차량 감지! 처음부터 재시작합니다.")
            print(f"   (이미 처리된 차량은 자동으로 건너뜁니다)")
            print(f"{'='*60}\n")
            return  # run_parking_automation 종료 → 외부 루프에서 재호출

    print(f"\n=== 이번 사이클 완료 ===")
    print(f"처리한 차량: {processed_count}대")
    print(f"성공: {success_count}대, 실패: {processed_count - success_count}대")

print("=== iParking 자동화 프로그램 시작 ===\n")

# 데이터 입력 방식 자동 선택 (최신 CSV가 있으면 자동 1번, 없으면 수동 입력)
latest_csv = CSV_FILES["1"]["path"]
if latest_csv and os.path.exists(latest_csv):
    INPUT_MODE = 'csv'
    CSV_FILE_PATH = latest_csv
    file_name = os.path.basename(latest_csv)
    file_time = datetime.fromtimestamp(os.path.getmtime(latest_csv)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"📁 주차_DB_파일 폴더에서 최신 파일 자동 선택됨:")
    print(f"   파일명: {file_name}")
    print(f"   수정시간: {file_time}")
    print(f"✅ '차량_DB (대량 등록용)' 모드로 자동 시작합니다.")
else:
    print("데이터 입력 방식을 선택하세요 (최신 CSV를 찾을 수 없음):")
    print("-" * 60)
    for key, info in CSV_FILES.items():
        file_path = info["path"]
        exists = "✓" if os.path.exists(file_path) else "✗"
        print(f"  {key}. {info['name']} {exists}")
    print(f"  2. 수동 입력 (이름 + 차량번호 직접 입력)")
    print("-" * 60)

    while True:
        choice = input("\n번호를 입력하세요 (1 또는 2): ").strip()
        
        if choice == "2":
            # 수동 입력 모드
            INPUT_MODE = 'manual'
            print(f"\n선택됨: 수동 입력 모드")
            break
            
        elif choice in CSV_FILES:
            # CSV 파일 모드
            INPUT_MODE = 'csv'
            default_path = CSV_FILES[choice]["path"]
            default_dir = CSV_FILES[choice].get("default_dir", "")
            
            print(f"\n선택됨: {CSV_FILES[choice]['name']}")
            
            # 옵션 1번이고 주차_DB_파일 폴더에 파일이 있는 경우
            if choice == "1" and default_path and os.path.exists(default_path):
                CSV_FILE_PATH = default_path
                break
            
            # 파일 존재 확인
            if os.path.exists(default_path):
                CSV_FILE_PATH = default_path
                break
            else:
                print(f"\n⚠️ 경고: 기본 파일을 찾을 수 없습니다!")
                # ... (이하 기존 파일 선택 대화상자 로직 유지 또는 간소화)
                selected_path = select_csv_file(default_path, default_dir)
                if selected_path and os.path.exists(selected_path):
                    CSV_FILE_PATH = selected_path
                    break
                else:
                    print("파일 선택 실패. 프로그램을 종료합니다.")
                    exit()
            break
        else:
            print("잘못된 입력입니다. 1 또는 2를 입력하세요.")

print("\n" + "="*60)

# Chrome 디버깅 모드 시작 및 연결

def cleanup_debug_chrome():
    """디버깅 모드로 실행된 Chrome 프로세스 정리"""
    try:
        print("\n기존 디버깅 Chrome 프로세스 확인 중...")
        # PowerShell 명령으로 디버깅 모드 Chrome 찾기
        cmd = 'Get-CimInstance Win32_Process -Filter "name = \'chrome.exe\'" | Where-Object { $_.CommandLine -like "*--remote-debugging-port=9222*" } | Select-Object ProcessId -ExpandProperty ProcessId'
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
        # 포트 9222가 이미 사용 중인지 확인 (socket 연결 테스트)
        print("포트 9222 상태 확인 중...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 9222))
        sock.close()
        
        if result == 0:
            print("  ✓ Chrome 디버깅 포트 9222가 이미 열려있습니다.")
            print("  → 기존 Chrome 세션을 사용합니다.")
            return True
        else:
            print(f"  ✗ 포트 9222 닫혀있음 (코드: {result})")
            print("  → 새 Chrome 디버깅 세션을 시작합니다.")
        
        # Chrome 디버깅 모드 시작
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        debug_dir = r"C:\chrome_debug_temp"
        
        # 디버그 디렉토리가 없으면 생성
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Chrome 디버깅 모드 실행 (새 창으로 표시) - iParking URL 3개 탭으로 시작
        iparking_url = "http://members.iparking.co.kr/html/login.html#!"
        cmd = f'start "" "{chrome_path}" --remote-debugging-port=9222 --user-data-dir="{debug_dir}" "{iparking_url}" "{iparking_url}" "{iparking_url}"'
        print(f"Chrome 디버깅 모드 시작 (iParking 탭 3개)")
        print("Chrome 창이 새로 열립니다. 잠시만 기다려주세요...")
        
        subprocess.Popen(cmd, shell=True)
        
        # Chrome이 디버깅 포트를 열고 페이지를 로드할 때까지 대기
        print("Chrome 초기화 및 페이지 로딩 중... (5초 대기)")
        time.sleep(5)
        
        return True
        
    except Exception as e:
        print(f"Chrome 디버깅 모드 시작 실패: {e}")
        return False

# 기존 디버깅 Chrome 정리
cleanup_debug_chrome()

# Chrome 디버깅 모드 시작
if not start_chrome_debug_mode():
    print("Chrome 디버깅 모드를 시작할 수 없습니다.")
    exit()

# 이미 로그인된 크롬 세션에 연결
try:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    # 연결 재시도 로직 추가
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Chrome 연결 시도 {attempt + 1}/{max_retries}...")
            driver = webdriver.Chrome(options=options)
            print("Chrome 연결 성공!")
            break
        except Exception as e:
            print(f"연결 시도 {attempt + 1} 실패: {e}")
            if attempt < max_retries - 1:
                print("5초 후 재시도...")
                time.sleep(5)
            else:
                raise e
    all_handles = driver.window_handles
    
    # Chrome 시작 시 이미 3개 탭이 열렸으므로 확인만 수행
    print("\n=== iParking 탭 확인 ===")
    
    # 사용할 iParking URL
    iparking_url = "http://members.iparking.co.kr/html/login.html#!"
    
    handles = []
    
    try:
        print(f"열린 탭 {len(all_handles)}개 확인 중...")
        
        # 모든 탭을 확인하고 iParking이 아닌 탭만 변경
        for i, handle in enumerate(all_handles):
            try:
                driver.switch_to.window(handle)
                time.sleep(0.5)  # 탭 전환 대기
                url = driver.current_url
                
                # iParking 페이지가 아니면 변경
                if 'iparking' not in url.lower():
                    print(f"  탭 {i+1}: 다른 페이지 감지, iParking으로 변경 중... (현재: {url[:50]})")
                    driver.get(iparking_url)
                    time.sleep(1.5)
                    print(f"  ✓ 탭 {i+1}: 변경 완료")
                else:
                    print(f"  ✓ 탭 {i+1}: iParking 페이지 확인됨")
                
                handles.append(handle)
                
            except Exception as e:
                print(f"  ✗ 탭 {i+1} 처리 중 오류: {e}")
        
        # 3개가 안되면 추가 생성
        while len(handles) < 3:
            try:
                tab_num = len(handles) + 1
                print(f"  추가 탭 {tab_num} 생성 중...")
                
                driver.execute_script(f"window.open('{iparking_url}', '_blank');")
                time.sleep(2)
                
                new_handles = driver.window_handles
                for handle in new_handles:
                    if handle not in handles:
                        driver.switch_to.window(handle)
                        handles.append(handle)
                        print(f"  ✓ 탭 {tab_num}: 생성 완료")
                        break
                        
            except Exception as e:
                print(f"  ✗ 탭 생성 중 오류: {e}")
                break
        
        print(f"==================")
        print(f"사용 가능한 iParking 탭 개수: {len(handles)}")
        
        if len(handles) == 0:
            print("iParking 탭을 생성할 수 없습니다!")
            exit()
        
        # 각 탭에 로그인 수행
        print("\n=== 계정 로그인 시작 ===")
        logged_in_count = 0
        
        for i, handle in enumerate(handles[:3]):  # 최대 3개 탭만 처리
            try:
                driver.switch_to.window(handle)
                time.sleep(1)
                current_url = driver.current_url
                
                # 이미 로그인되어 있는지 확인
                if 'login' not in current_url:
                    print(f"  ✓ 탭 {i+1}: 이미 로그인됨 ({ACCOUNTS[i]['username']})")
                    logged_in_count += 1
                else:
                    # 로그인 필요
                    print(f"  탭 {i+1}: {ACCOUNTS[i]['username']} 로그인 중...")
                    if login_to_iparking(driver, ACCOUNTS[i]['username'], ACCOUNTS[i]['password']):
                        # 로그인 후 URL 확인
                        time.sleep(2)
                        if 'login' not in driver.current_url:
                            print(f"    ✓ 로그인 성공!")
                            logged_in_count += 1
                        else:
                            print(f"    ✗ 로그인 실패 (아이디/비밀번호 확인 필요)")
                    
            except Exception as e:
                print(f"  ✗ 탭 {i+1} 로그인 중 오류: {e}")
        
        print(f"==================")
        print(f"로그인 완료: {logged_in_count}/{len(handles[:3])}개 계정")
        
        if logged_in_count == 0:
            print("\n[!] 모든 계정 로그인 실패!")
            print("아이디/비밀번호를 확인하거나 수동으로 로그인해주세요.")
            exit()
            
    except Exception as e:
        print(f"iParking 탭 생성 실패: {e}")
        exit()
    
    # 첫 번째 탭으로 이동
    driver.switch_to.window(handles[0])
    print(f"첫 번째 탭으로 이동 완료\n")
    
except Exception as e:
    print(f"크롬 브라우저 연결 실패: {e}")
    print("해결 방법:")
    print("1. Chrome이 설치되어 있는지 확인하세요.")
    print("2. 수동으로 Chrome 디버깅 모드를 실행해보세요:")
    print('   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\chrome_debug_temp"')
    print("3. 방화벽이나 보안 프로그램이 포트 9222를 차단하고 있는지 확인하세요.")
    input("Enter를 눌러 프로그램을 종료하세요...")
    exit()

# 데이터 소스 확인
if INPUT_MODE == 'manual':
    print(f"\n수동 입력 모드 준비 완료 ✓")
else:
    print(f"\n사용 중인 CSV 파일: {os.path.basename(CSV_FILE_PATH)}")
    print("CSV 파일 준비 완료 ✓")

# 실행 모드에 따라 반복 또는 단일 실행
if INPUT_MODE == 'manual':
    # 수동 입력 모드: 반복 입력 가능
    print("\n수동 입력 모드 - 계속해서 차량 정보를 입력할 수 있습니다.")
    print("각 입력 후 자동으로 처리되며, 종료하려면 입력 시 'q' 또는 'quit'를 입력하세요.")
    print("="*50)
    
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"\n{'='*50}")
            print(f"수동 입력 사이클 {cycle_count}")
            print(f"{'='*50}")
            
            # 수동 입력 받기
            input_result = get_manual_input()
            
            # 종료 신호 확인
            if input_result == False:
                print("\n프로그램을 종료합니다.")
                break
            
            # 입력 없음 확인
            if input_result == None:
                print("\n입력된 데이터가 없습니다. 다시 입력하거나 종료하려면 'q'를 입력하세요.")
                continue
            
            # 수동 입력 데이터 준비 완료
            log_to_file(f"수동 입력 데이터: {len(MANUAL_DATA)}개 차량")
            update_bot_heartbeat("Processing", f"수동 입력 {len(MANUAL_DATA)}건 처리 시작")
            
            # 자동화 실행
            run_parking_automation()
            
            # 자동 GitHub 업로드
            auto_push_to_github()
            
            update_bot_heartbeat("Alive", "수동 입력 처리 완료")
            log_to_file("처리 완료! 다음 입력을 기다립니다...")
            print("(종료하려면 다음 입력 시 'q' 또는 'quit' 입력)")
            
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
        print("=== iParking 자동화 프로그램 종료 ===")
else:
    # CSV 파일 모드: 5분마다 반복 실행
    print("300초(5분)마다 자동화 실행을 시작합니다...")
    print("프로그램을 중단하려면 Ctrl+C를 누르세요.")

    # ========================================
    # 🚨 신규 일일 등록 감지 백그라운드 스레드 시작
    # ========================================
    print("\n🔍 신규 일일 등록 감지 시스템 활성화...")
    detection_thread = threading.Thread(target=check_new_daily_background, daemon=True)
    detection_thread.start()
    print("✅ 5분마다 신규 일일 차량을 감지합니다.\n")

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            log_to_file(f"{'='*50}")
            log_to_file(f"사이클 {cycle_count} 시작")
            log_to_file(f"{'='*50}")
            
            update_bot_heartbeat("Processing", f"{cycle_count}번째 사이클 시작")
            
            # 자동화 실행
            try:
                run_parking_automation()
                update_bot_heartbeat("Alive", f"{cycle_count}번째 사이클 완료")
            except Exception as e:
                log_to_file(f"❌ 자동화 도중 치명적 오류: {e}", "ERROR")
                update_bot_heartbeat("Error", f"자동화 오류: {str(e)}")
            
            # 자동 GitHub 업로드
            auto_push_to_github()
            
            log_to_file(f"다음 실행까지 300초(5분) 대기 중...")
            log_to_file(f"다음 실행 예정 시간: {(datetime.now() + timedelta(seconds=300)).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 300초 대기
            time.sleep(300)
            
    except KeyboardInterrupt:
        log_to_file("프로그램이 사용자에 의해 중단되었습니다.")
        update_bot_heartbeat("Stopped", "사용자가 중단함")
        log_to_file("디버깅 Chrome 정리 중...")
        cleanup_debug_chrome()
        log_to_file("=== iParking 자동화 프로그램 종료 ===")