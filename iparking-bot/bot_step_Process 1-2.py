# iParking 자동화 1-2단계: 입차 여부 검사 및 리스트 생성
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_temp"
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import gspread
from google.oauth2.service_account import Credentials
import re
from datetime import datetime
import pandas as pd
import subprocess

def check_car_entered(driver, car_number_full):
    """
    차량번호로 실제 입차 여부만 확인하는 함수.
    '검색된 차량이 없습니다.' 메시지가 있으면 'not_entered',
    검색 결과 테이블에 차량번호가 정확히 일치하면 'entered' 반환.
    """
    wait = WebDriverWait(driver, 3)
    try:
        input_box = wait.until(EC.element_to_be_clickable((By.ID, "carNumber")))
        input_box.clear()
        last4 = car_number_full.replace(" ", "")[-4:]
        input_box.send_keys(last4)
        driver.find_element(By.CLASS_NAME, "btn-search").click()
        time.sleep(1)  # 검색 결과가 뜨는 시간 약간 대기

        # 1. "검색된 차량이 없습니다." 메시지 감지
        try:
            no_result = driver.find_element(By.ID, "parkName")
            if no_result.text.strip() == "검색된 차량이 없습니다.":
                print("차량 없음 메시지 감지, 홈 버튼 클릭 (입차 확인)")
                try:
                    home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                    home_btn_right.click()
                except Exception as e:
                    print(f"홈 버튼 클릭 실패(차량 없음 처리 중): {e}")
                return "not_entered"
        except Exception:
            # parkName 요소가 없으면 계속 진행
            pass

        # 2. 검색 결과 테이블에서 차량번호가 정확히 일치하는지 확인
        # (예: <td>351도6331</td>)
        found = False
        tds = driver.find_elements(By.TAG_NAME, "td")
        search_number = normalize_car_number(car_number_full)
        # 디버깅: 다양한 태그에서 차량번호 추출 시도
        for tag in ["td", "span", "div"]:
            elements = driver.find_elements(By.TAG_NAME, tag)
            print(f"[DEBUG] {tag} 태그 개수: {len(elements)}")
            for el in elements:
                print(f"[DEBUG] {tag} 내용: '{el.text}'")
        for td in tds:
            td_number = normalize_car_number(td.text)
            if td_number == search_number:
                found = True
                break

        if found:
            print(f"차량 {car_number_full} 입차 확인됨")
            return "entered"
        else:
            print(f"차량 {car_number_full} 검색 결과 없음(미입차 처리)")
            return "not_entered"

    except Exception as e:
        print(f"입차 확인 중 오류: {e}")
        try:
            home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
            home_btn_right.click()
        except Exception as e2:
            print(f"오른쪽 상단 홈 버튼 클릭 실패(입차 확인): {e2}")
        return "not_entered"

# 차량번호 정규화 함수 (한글, 숫자만 남김)
def normalize_car_number(car_number):
    return re.sub(r'[^가-힣0-9]', '', car_number)

# === 사이클 번호 자동 증가 ===
# A열에서 가장 큰 회차 번호를 찾아서 +1
import re as _re

def get_next_cycle_number(db_copy_rows):
    max_cycle = 0
    for row in db_copy_rows[2:]:
        a_val = row[0] if len(row) > 0 else ""
        m = _re.match(r"(\d+)회차", a_val)
        if m:
            n = int(m.group(1))
            if n > max_cycle:
                max_cycle = n
    return max_cycle + 1 if max_cycle > 0 else 1

print("=== iParking 반복 사이클: 입차 여부 검사 시작 ===")

def start_chrome_debug_mode():
    # 디버깅 포트가 이미 사용 중인지 확인
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 9222))
    sock.close()
    
    if result == 0:
        print("디버깅 포트 9222가 이미 사용 중입니다. 기존 디버깅 세션을 사용합니다.")
    else:
        print("새로운 크롬 디버깅 모드를 실행합니다.")
        # 크롬 디버깅 모드 실행
        subprocess.Popen([
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "--remote-debugging-port=9222",
            "--user-data-dir=C:\\chrome_debug_temp",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions"
        ])
        print("크롬 실행 완료 대기 중...")
        time.sleep(1)  # 크롬이 완전히 실행될 때까지 충분히 대기

def open_chrome_and_login(url, user_credentials):
    print("크롬에 연결을 시도합니다...")
    
    # 연결 재시도 로직 추가
    max_retries = 5
    driver = None
    
    for attempt in range(max_retries):
        try:
            print(f"연결 시도 {attempt + 1}/{max_retries}")
            options = webdriver.ChromeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)
            print("크롬 연결 성공!")
            
            # 연결 테스트
            current_handles = driver.window_handles
            print(f"현재 열려있는 탭 수: {len(current_handles)}")
            break
            
        except Exception as e:
            print(f"크롬 연결 시도 {attempt + 1}/{max_retries} 실패: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if attempt < max_retries - 1:
                print("5초 후 재시도...")
                time.sleep(5)
            else:
                print("크롬 연결에 실패했습니다.")
                raise e

    # 기존의 모든 탭을 닫고 새로 시작 (순서 보장을 위해)
    current_handles = driver.window_handles
    print(f"기존 탭 {len(current_handles)}개를 정리하고 새로 시작합니다...")
    
    # 첫 번째 탭만 남기고 나머지 닫기
    main_handle = current_handles[0]
    for handle in current_handles[1:]:
        try:
            driver.switch_to.window(handle)
            driver.close()
            print(f"기존 탭 닫기 완료: {handle[:8]}...")
        except Exception as e:
            print(f"탭 닫기 실패: {e}")
    
    # 메인 탭으로 돌아가기
    driver.switch_to.window(main_handle)
    time.sleep(1)
    
    # 정확히 3개의 탭을 순서대로 생성
    tab_handles = [main_handle]  # 첫 번째 탭 (기존)
    
    # 2번째, 3번째 탭 생성
    for i in range(2):
        try:
            driver.execute_script("window.open('about:blank');")
            time.sleep(1)  # 탭 생성 대기
            new_handles = driver.window_handles
            new_handle = [h for h in new_handles if h not in tab_handles][0]
            tab_handles.append(new_handle)
            print(f"탭 {i+2} 생성 완료: {new_handle[:8]}...")
        except Exception as e:
            print(f"탭 {i+2} 생성 실패: {e}")
    
    print(f"=== 탭 생성 완료 (총 {len(tab_handles)}개) ===")
    for i, handle in enumerate(tab_handles):
        print(f"탭 {i+1}: {handle[:8]}...")
    
    # 각 탭에 순서대로 로그인 처리 (생성 순서 = 물리적 순서)
    for i, handle in enumerate(tab_handles[:3]):
        try:
            driver.switch_to.window(handle)
            print(f"탭 {i+1} 처리 시작 (handle: {handle[:8]}...)...")
            
            # URL로 이동
            driver.get(url)
            time.sleep(1)  # 페이지 로딩 충분히 대기

            # 로그인 상태 확인 (예: 특정 요소가 있는지 확인)
            try:
                driver.find_element(By.ID, "storeSelect")
                print(f"탭 {i+1} 이미 로그인됨, 로그인 건너뜀")
                continue
            except:
                pass

            # 로그인 정보 입력 (순서대로 계정 매칭)
            if i < len(user_credentials):
                user_id, user_pw = user_credentials[i]
                print(f"탭 {i+1}에 {user_id} 계정으로 로그인 시도...")
                
                # 로그인 폼 요소 대기 및 입력
                wait = WebDriverWait(driver, 10)
                id_input = wait.until(EC.element_to_be_clickable((By.ID, "id")))
                id_input.clear()
                id_input.send_keys(user_id)
                
                pw_input = driver.find_element(By.ID, "password")
                pw_input.clear()
                pw_input.send_keys(user_pw)
                
                login_btn = driver.find_element(By.ID, "login")
                login_btn.click()
                print(f"탭 {i+1} ({user_id}) 로그인 완료")
                time.sleep(1)  # 로그인 처리 대기
                
                # 로그인 성공 확인
                try:
                    time.sleep(2)
                    current_store = driver.find_element(By.ID, "storeSelect")
                    print(f"✅ 탭 {i+1} - {user_id} 로그인 성공 확인")
                except:
                    print(f"⚠️ 탭 {i+1} - {user_id} 로그인 상태 확인 실패")
            else:
                print(f"탭 {i+1}에 대한 계정 정보가 없습니다.")
                
        except Exception as e:
            print(f"탭 {i+1} 처리 실패: {e}")

    print("모든 탭 준비가 완료되었습니다.")
    return driver

# 프로그램 시작 시 크롬 디버깅 모드 실행
start_chrome_debug_mode()

# 사용 예시
url = "http://members.iparking.co.kr/html/login.html#!"  # iParking 사이트의 로그인 URL
user_credentials = [
    ("dreamcb01", "dreamcb01"),
    ("dreamcb02", "dreamcb02"),
    ("dreamcb03", "dreamcb03")
]

driver = open_chrome_and_login(url, user_credentials)
print("3개의 탭이 생성되고 로그인이 완료되었습니다.")

# 이미 로그인된 크롬 세션에 연결
try:
    # 기존에 생성된 driver 사용
    handles = sorted(driver.window_handles)
    print(f"크롬 브라우저 연결 완료. 탭 개수: {len(handles)}")
except Exception as e:
    print(f"크롬 브라우저 연결 실패: {e}")
    exit()

# 디버깅 모드로 실행된 창의 핸들만 필터링 (예: 특정 URL이나 제목으로 필터링)
debug_handles = []
for handle in handles:
    driver.switch_to.window(handle)
    # 예를 들어, 디버깅 모드 창의 URL에 특정 문자열이 포함되어 있다고 가정
    if "특정_조건" in driver.current_url:  # 또는 driver.title
        debug_handles.append(handle)

# 필터링된 핸들로 작업 수행
for handle in debug_handles:
    driver.switch_to.window(handle)
    # 여기서 원하는 작업 수행

# 구글 시트 연결
try:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = 'iparking-auto-주차등록.json'
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    SPREADSHEET_ID = '1aq3L5JlCHfE-XUECLFEzaTv4MqOCcfbYLTmQSaR5wVE'
    sh = gc.open_by_key(SPREADSHEET_ID)
    print("구글 시트 연결 완료")
except Exception as e:
    print(f"구글 시트 연결 실패: {e}")
    exit()

# 차량_DB 시트의 사본 접근
try:
    db_worksheet = sh.worksheet('차량_DB 시트')
    print("차량_DB 시트 접근 완료")
except Exception as e:
    print(f"차량_DB 시트 접근 실패: {e}")
    exit()

print("\n=== 1단계: 입차 여부 검사 및 표기 ===")
db_copy_rows = db_worksheet.get_all_values()
cycle_number = get_next_cycle_number(db_copy_rows)
cycle_label = f"{cycle_number}회차"
processed_count = 0
update_values = []  # 한 번에 업데이트할 값 리스트
update_start_row = 3  # D3:E... 시작 행
for idx, row in enumerate(db_copy_rows[2:], start=3):  # 3번째 줄부터
    a_val = row[0] if len(row) > 0 else ""
    name = row[1] if len(row) > 1 else ""
    car_number = row[2] if len(row) > 2 else ""
    status = row[3] if len(row) > 3 else ""
    prev_time = row[4] if len(row) > 4 else ""
    entry_time = ""  # 입차 일시 초기화
    # D열이 '미입차' 또는 빈 칸인 차량만 검사
    if status == "입차":
        update_values.append([
            cycle_label,   # A: 회차
            name,          # B: 이름 (기존 값 유지)
            car_number,    # C: 차번호 (기존 값 유지)
            status,        # D: 입차 여부
            prev_time,     # E: 입차확인시간 (기존 값 유지)
            prev_time      # F: 실입차시간 (기존 값 유지)
        ])
        continue
    if not car_number.strip():
        update_values.append([
            cycle_label,   # A: 회차
            "",            # B: 이름 (빈칸)
            "",            # C: 차번호 (빈칸)
            "",            # D: 입차여부 (미입차)
            "",            # E: 입차확인시간 (빈칸)
            ""            # F: 실입차시간 (빈칸)
        ])
        continue
    print(f"{car_number} - 입차 여부 확인 중...")
    result = check_car_entered(driver, car_number)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if result == "entered":
        status = "입차"
        print(f"{car_number} - 입차 확인됨")
        # 입차 일시 추출 (테이블에서 날짜/시간 형식 찾기)
        tds = driver.find_elements(By.TAG_NAME, "td")
        for td in tds:
            if re.match(r"\d{2}\.\d{2}\.\d{2} \d{2}:\d{2}", td.text.strip()):
                entry_time = td.text.strip()
                break
        # E열(now_str)과 F열(entry_time) 차이 계산
        try:
            entry_dt = datetime.strptime(entry_time, "%y.%m.%d %H:%M") if entry_time else None
            check_dt = datetime.strptime(now_str, "%Y-%m-%d %H:%M:%S")
            if entry_dt and (check_dt - entry_dt).total_seconds() >= 86400:
                status = "미입차(veo)"
                print(f"{car_number} - 미입차 처리됨 (veo, 입차확인:{now_str}, 실입차:{entry_time})")
        except Exception as e:
            print(f"시간 비교 오류: {e}")
    else:
        status = "미입차"
        print(f"{car_number} - 미입차 처리됨")
    processed_count += 1
    # 이번 사이클에 검사한 차량만 A/D/E열 갱신
    update_values.append([
        cycle_label,   # A: 회차
        name,          # B: 이름
        car_number,    # C: 차번호
        status,        # D: 입차 여부
        now_str,       # E: 입차 확인 시간
        entry_time     # F: 실입차 시간
    ])

    # 10개마다 시트에 일괄 업데이트
    if processed_count % 10 == 0:
        update_range = f'A{update_start_row}:F{update_start_row + len(update_values) - 1}'
        db_worksheet.update(update_range, update_values)
        print(f"{processed_count}대 차량 입차 여부를 시트에 반영했습니다.")
        update_start_row += len(update_values)
        update_values = []

# 남은 차량이 있으면 마지막으로 업데이트
if update_values:
    update_range = f'A{update_start_row}:F{update_start_row + len(update_values) - 1}'
    db_worksheet.update(update_range, update_values)
    print(f"마지막 {len(update_values)}대 차량 입차 여부를 시트에 반영했습니다.")

print(f"\n총 {processed_count}대 차량 입차 여부 검사 완료")

print("\n=== 2단계: 입차 차량 리스트 생성 ===")
db_copy_rows = db_worksheet.get_all_values()
entered_rows = []
for row in db_copy_rows[2:]:
    a_val = row[0] if len(row) > 0 else ""
    name = row[1] if len(row) > 1 else ""
    car_number = row[2] if len(row) > 2 else ""
    status = row[3] if len(row) > 3 else ""
    in_time = row[4] if len(row) > 4 else ""  # 입차확인시간
    entry_time = row[5] if len(row) > 5 else ""  # 실입차시간
    # 상태가 '입차'인 경우만 리스트에 포함 (미입차, 미입차(사유) 등은 제외)
    if status == "입차":
        entered_rows.append((in_time, name, car_number))
        print(f"{car_number} - 입차 차량으로 확인됨")

print("\n입차 차량 총 {}대 발견".format(len(entered_rows)))

if len(entered_rows) == 0:
    print("입차된 차량이 없습니다.")
else:
    print("\n=== 입차 차량 목록 ===")
    for idx, (in_time, name, car_number) in enumerate(entered_rows, 1):
        print(f"{idx}. {car_number} ({name}) - 입차시간: {in_time}")

    print("\n=== 입차 차량 명단을 '주차등록 차량 명단 시트'에 복사합니다 ===")
    try:
        parking_reg_worksheet = sh.worksheet('주차등록 차량 명단 시트')
        parking_reg_worksheet.update([['번호','입차 확인 시간','성도명', '차량번호', '상태', '처리 시간']], 'A1:F1')
        for idx, (in_time, name, car_number) in enumerate(entered_rows):
            parking_reg_worksheet.update_cell(idx + 2, 2, in_time)      # B열: 입차 확인 시간
            parking_reg_worksheet.update_cell(idx + 2, 3, name)         # C열: 성도명
            parking_reg_worksheet.update_cell(idx + 2, 4, car_number)   # D열: 차량번호
            print(f"{car_number} - 주차등록 차량 명단에 복사 완료")
        print("입차 차량 명단이 '주차등록 차량 명단 시트'에 기록되었습니다.")
    except Exception as e:
        print(f"'주차등록 차량 명단 시트' 기록 실패: {e}")

print("\n=== 1-2단계 완료 ===")
print("입차 여부 검사 및 리스트 생성이 완료되었습니다.")
print("이제 3-4단계(주차권 등록)를 실행할 수 있습니다.") 