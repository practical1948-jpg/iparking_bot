# iParking 자동화 3-4단계: 주차권 등록 자동화
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

def check_limit_popup(driver, wait):
    try:
        popup = wait.until(EC.presence_of_element_located((By.ID, "popMessage")))
        if "멤버스 상점 할인 제한 횟수를 초과하였습니다." in popup.text:
            print("할인 제한 팝업 감지, 홈 버튼 클릭")
            ok_btn = wait.until(EC.element_to_be_clickable((By.ID, "popupOk")))
            ok_btn.click()
            home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
            home_btn_right.click()
            return True
    except Exception as e:
        # print(f"팝업 체크 중 예외: {e}")
        pass
    return False

def apply_discount(driver, car_number_full):
    wait = WebDriverWait(driver, 3)
    try:
        input_box = wait.until(EC.element_to_be_clickable((By.ID, "carNumber")))
        input_box.clear()
        last4 = car_number_full[-4:]
        input_box.send_keys(last4)
        driver.find_element(By.CLASS_NAME, "btn-search").click()
        # 차량 없음 메시지
        try:
            no_result = wait.until(EC.presence_of_element_located((By.ID, "parkName")))
            if "검색된 차량이 없습니다." in no_result.text:
                print("차량 없음 메시지 감지, 홈 버튼 클릭")
                try:
                    home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                    home_btn_right.click()
                except Exception as e:
                    print(f"홈 버튼 클릭 실패(차량 없음 처리 중): {e}")
                return "no_car"
        except Exception as e:
            print(f"차량 없음 메시지 감지 중 예외: {e}")
            # pass로 두면 이후 코드에서 또 예외가 발생할 수 있음

        # Process 1-2와 동일한 방식으로 모든 td 요소에서 검색
        tds = driver.find_elements(By.TAG_NAME, "td")
        search_number = normalize_car_number(car_number_full)
        found = False
        found_element = None
        
        print(f"DEBUG: 찾고 있는 차량번호(정규화): '{search_number}'")
        print(f"DEBUG: 검색된 td 요소 개수: {len(tds)}")
        
        for td in tds:
            if td.text.strip():  # 빈 셀 제외
                td_number = normalize_car_number(td.text)
                print(f"DEBUG: 비교 중 - '{td.text}' -> 정규화: '{td_number}'")
                if td_number == search_number:
                    print(f"DEBUG: 일치 발견! 클릭 시도")
                    found_element = td
                    found = True
                    break
        
        if not found:
            # 일치하는 차량번호가 없으면 홈으로 복귀 및 no_car 반환
            try:
                home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                home_btn_right.click()
            except Exception:
                pass
            return "no_car"
        
        # 찾은 요소 클릭
        found_element.click()

        select_btn = wait.until(EC.element_to_be_clickable((By.ID, "next")))
        select_btn.click()

        apply_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-apply")))
        apply_btn.click()

        # 할인 제한 팝업 감지 (적용 버튼 클릭 후 - 가장 중요한 시점)
        if check_limit_popup(driver, wait):
            return "limit"

        try:
            ok_btn = wait.until(EC.element_to_be_clickable((By.ID, "popupOk")))
            ok_btn.click()
            # 첫 번째 확인 후에도 팝업 체크
            if check_limit_popup(driver, wait):
                return "limit"
            ok_btn2 = wait.until(EC.element_to_be_clickable((By.ID, "popupOk")))
            ok_btn2.click()
            home_btn = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
            home_btn.click()
            print("탭에서 성공적으로 완료됨")
            return "success"
        except Exception as e:
            print(f"팝업 처리 중 오류: {e}")
            if check_limit_popup(driver, wait):
                return "limit"
            return f"error:팝업 처리 중 오류:{e}"
    except Exception as e:
        print(f"탭에서 오류 발생: {e}")
        if check_limit_popup(driver, wait):
            return "limit"
        try:
            home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
            home_btn_right.click()
            print("오른쪽 상단 홈 버튼 클릭 후 다음 탭으로 이동")
        except Exception as e2:
            print(f"오른쪽 상단 홈 버튼 클릭 실패: {e2}")
        return f"error:탭 전체 오류:{e}"

# 차량번호 정규화 함수 (한글, 숫자만 남김)
def normalize_car_number(car_number):
    return re.sub(r'[^가-힣0-9]', '', car_number)

print("=== iParking 3-4단계: 주차권 등록 자동화 시작 ===")

# 이미 로그인된 크롬 세션에 연결
try:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)
    handles = driver.window_handles
    print(f"크롬 브라우저 연결 완료. 탭 개수: {len(handles)}")
except Exception as e:
    print(f"크롬 브라우저 연결 실패: {e}")
    exit()

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

print("\n=== 입차 차량 리스트 읽기 ===")
# 입차된 차량 리스트 생성 (이미 1-2단계에서 처리된 데이터 읽기)
db_copy_rows = db_worksheet.get_all_values()
entered_rows = []
for row in db_copy_rows[2:]:
    name = row[1] if len(row) > 1 else ""
    car_number = row[2] if len(row) > 2 else ""
    status = row[3] if len(row) > 3 else ""
    in_time = row[4] if len(row) > 4 else ""  # 입차확인시간
    
    if status == "입차":
        entered_rows.append((in_time, name, car_number))
        print(f"{car_number} - 입차 차량으로 확인됨")

print(f"\n입차 차량 총 {len(entered_rows)}대 발견")

if len(entered_rows) == 0:
    print("입차된 차량이 없습니다. 먼저 1-2단계를 실행해주세요.")
    exit()

print("\n=== 3단계: 주차등록 차량 명단 시트에 복사 ===")
# 주차등록 차량 명단 시트에 복사
try:
    parking_reg_worksheet = sh.worksheet('주차등록 차량 명단 시트')
    print("주차등록 차량 명단 시트 접근 완료")
except Exception as e:
    print(f"주차등록 차량 명단 시트 접근 실패: {e}")
    exit()

# 헤더 설정
parking_reg_worksheet.update([['번호','입차 확인 시간','성도명', '차량번호', '상태', '처리 시간']], 'A1:F1')

# 입차 차량 정보 복사 (2번째 줄부터)
for idx, (in_time, name, car_number) in enumerate(entered_rows):
    parking_reg_worksheet.update_cell(idx + 2, 2, in_time)      # B열: 입차 확인 시간
    parking_reg_worksheet.update_cell(idx + 2, 3, name)         # C열: 성도명
    parking_reg_worksheet.update_cell(idx + 2, 4, car_number)   # D열: 차량번호
    print(f"{car_number} - 주차등록 차량 명단에 복사 완료")

print(f"\n=== 4단계: 주차권 등록 자동화 (총 {len(entered_rows)}대) ===")
# 주차권 등록 자동화
car_numbers = parking_reg_worksheet.col_values(4)[1:]  # D열(차량번호), [1:]로 헤더 제외

success_count = 0
fail_count = 0
status_update = []  # 결과를 모을 리스트

for idx, car_number in enumerate(car_numbers):
    if not car_number.strip():
        status_update.append(["", ""])
        continue
        
    print(f"\n[{idx+1}/{len(car_numbers)}] {car_number} - 주차권 등록 시작")
    tab_results = []
    
    # 3개 탭에서 순차적으로 등록 시도
    for tab_idx in range(len(handles)):
        driver.switch_to.window(handles[tab_idx])
        print(f"  {tab_idx+1}번째 탭에서 시도 중...")
        result = apply_discount(driver, car_number)
        tab_results.append(result)
        print(f"  {tab_idx+1}번째 탭 결과: {result}")
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if all(r == "success" for r in tab_results):
        status_update.append(["성공", now_str])
        print(f"  {car_number} - 최종 결과: 성공 (3개 탭 모두 성공)")
        success_count += 1
    else:
        status_update.append(["실패 (오류 : 탭)", now_str])
        print(f"  {car_number} - 최종 결과: 실패 (하나 이상의 탭에서 실패)")
        fail_count += 1

# === 여기서 한 번에 업데이트 ===
update_range = f'E2:F{len(car_numbers)+1}'
parking_reg_worksheet.update(update_range, status_update)

print("\n=== 3-4단계 완료 ===")
print(f"주차권 등록 완료: 성공 {success_count}대, 실패 {fail_count}대")
print("모든 주차권 등록 작업이 완료되었습니다.") 