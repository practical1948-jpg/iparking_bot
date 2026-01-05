# 크롬 브라우저에서 멤버스 상점 할인 적용 자동화 스크립트 - 전체 백업
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

        results = driver.find_elements(By.CSS_SELECTOR, ".car-number-cell")
        search_last4 = car_number_full.replace(" ", "")[-4:]
        for result in results:
            td_last4 = result.text.replace(" ", "")[-4:]
            if td_last4 == search_last4:
                result.click()
                break

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
        search_last4 = car_number_full.replace(" ", "")[-4:]
        for td in tds:
            td_last4 = td.text.replace(" ", "")[-4:]
            if td_last4 == search_last4:
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

print("=== iParking 자동화 프로그램 시작 ===")

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

print("\n=== 1단계: 입차 여부 검사 및 표기 ===")
# 1단계: 입차 여부 검사 및 표기
db_copy_rows = db_worksheet.get_all_values()
for idx, row in enumerate(db_copy_rows[2:], start=3):  # 3번째 줄부터
    name = row[1] if len(row) > 1 else ""
    car_number = row[2] if len(row) > 2 else ""
    status = row[3] if len(row) > 3 else ""
    
    if not car_number.strip():
        continue
    
    if status == "입차" or status == "미입차":
        print(f"{car_number} - 이미 처리됨 ({status})")
        continue
    
    print(f"{car_number} - 입차 여부 확인 중...")
    result = check_car_entered(driver, car_number)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if result == "entered":
        db_worksheet.update_cell(idx, 4, "입차")
        db_worksheet.update_cell(idx, 5, now_str)  # E열에 처리 시각 기록
        print(f"{car_number} - 입차 확인됨")
    else:
        db_worksheet.update_cell(idx, 4, "미입차")
        db_worksheet.update_cell(idx, 5, now_str)  # E열에 처리 시각 기록
        print(f"{car_number} - 미입차 처리됨")

print("\n=== 2단계: 입차 차량 리스트 생성 ===")
# 입차된 차량 리스트 생성
db_copy_rows = db_worksheet.get_all_values()
entered_rows = []
for row in db_copy_rows[2:]:
    name = row[1] if len(row) > 1 else ""
    car_number = row[2] if len(row) > 2 else ""
    status = row[3] if len(row) > 3 else ""
    in_time = row[4] if len(row) > 4 else ""  # 입차확인시간
    
    if status == "입차":
        entered_rows.append((in_time, name, car_number))

print(f"입차 차량 총 {len(entered_rows)}대 발견")

if len(entered_rows) == 0:
    print("입차된 차량이 없습니다. 프로그램을 종료합니다.")
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

for idx, car_number in enumerate(car_numbers):
    if not car_number.strip():
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
    
    # 최종 처리 시간
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 3개 탭 모두 성공해야 성공, 하나라도 실패면 실패
    if all(r == "success" for r in tab_results):
        parking_reg_worksheet.update_cell(idx + 2, 5, "성공")         # E열: 상태
        parking_reg_worksheet.update_cell(idx + 2, 6, now_str)         # F열: 처리 시간
        print(f"  {car_number} - 최종 결과: 성공 (3개 탭 모두 성공)")
    else:
        parking_reg_worksheet.update_cell(idx + 2, 5, "실패 (오류 : 탭)")  # E열: 상태(간단 사유)
        parking_reg_worksheet.update_cell(idx + 2, 6, now_str)         # F열: 처리 시간
        print(f"  {car_number} - 최종 결과: 실패 (하나 이상의 탭에서 실패)")

print("\n=== iParking 자동화 프로그램 완료 ===")
print("모든 작업이 완료되었습니다.") 