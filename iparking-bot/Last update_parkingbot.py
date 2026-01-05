# iParking 통합 자동화 프로그램: Last Update + Simple Logic 순차 실행
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_temp"
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import gspread
from google.oauth2.service_account import Credentials
import re
from datetime import datetime, timedelta
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
        # 현재 페이지 정보 확인
        print(f"[DEBUG] 현재 URL: {driver.current_url}")
        print(f"[DEBUG] 현재 페이지 제목: {driver.title}")
        
        try:
            input_box = wait.until(EC.element_to_be_clickable((By.ID, "carNumber")))
            print("[DEBUG] carNumber 입력창 찾기 성공")
        except Exception as e:
            print(f"[DEBUG] carNumber 입력창 찾기 실패: {e}")
            # 페이지의 모든 input 요소 확인
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"[DEBUG] 페이지의 input 요소 개수: {len(inputs)}")
            for i, inp in enumerate(inputs):
                inp_id = inp.get_attribute("id")
                inp_name = inp.get_attribute("name")
                inp_type = inp.get_attribute("type")
                print(f"[DEBUG] input[{i}]: id='{inp_id}', name='{inp_name}', type='{inp_type}'")
            raise
        input_box.clear()
        last4 = car_number_full.replace(" ", "")[-4:]
        input_box.send_keys(last4)
        print(f"[DEBUG] 검색어 입력: '{last4}'")
        try:
            search_btn = driver.find_element(By.CLASS_NAME, "btn-search")
            print("[DEBUG] 검색 버튼 찾기 성공")
        except Exception as e:
            print(f"[DEBUG] 검색 버튼 찾기 실패: {e}")
            raise
        search_btn.click()
        print("[DEBUG] 검색 버튼 클릭 완료")
        time.sleep(3)  # 검색 결과가 뜨는 시간을 3초로 늘림

        # 1. "검색된 차량이 없습니다." 메시지 감지
        try:
            no_result = driver.find_element(By.ID, "parkName")
            if no_result.text.strip() == "검색된 차량이 없습니다.":
                print("[DEBUG] '검색된 차량이 없습니다.' 메시지 감지")
                try:
                    home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
                    home_btn_right.click()
                except Exception as e:
                    print(f"홈 버튼 클릭 실패(차량 없음 처리 중): {e}")
                return "not_entered"
        except Exception:
            print("[DEBUG] parkName 요소 없음, 검색 결과 있음으로 판단")
            pass

        # 모든 태그에서 텍스트 추출 (디버깅 강화)
        for tag in ["td", "span", "div"]:
            elements = driver.find_elements(By.TAG_NAME, tag)
            print(f"[DEBUG] {tag} 태그 개수: {len(elements)}")
            for i, el in enumerate(elements):
                if el.text.strip():
                    print(f"[DEBUG] {tag}[{i}]: '{el.text}'")

        # Simple_logic.py 방식: .car-number-cell class 우선, 없으면 td 태그로 재시도
        results = driver.find_elements(By.CSS_SELECTOR, ".car-number-cell")
        print(f"[DEBUG] .car-number-cell로 찾은 요소 개수: {len(results)}")
        for i, result in enumerate(results):
            print(f"[DEBUG] 요소 {i+1}: '{result.text}'")
        if len(results) == 0:
            print("[DEBUG] .car-number-cell 요소가 없어서 td 태그로 재시도")
            results = driver.find_elements(By.TAG_NAME, "td")
            print(f"[DEBUG] td 태그로 찾은 요소 개수: {len(results)}")
            for i, result in enumerate(results):
                if result.text.strip():
                    print(f"[DEBUG] td 요소 {i+1}: '{result.text}'")
        
        search_number = normalize_car_number(car_number_full)
        print(f"[DEBUG] 찾고 있는 차량번호(정규화): '{search_number}'")
        found = False
        for i, result in enumerate(results):
            td_number = normalize_car_number(result.text)
            print(f"[DEBUG] 비교[{i}]: '{result.text}' -> 정규화: '{td_number}' vs '{search_number}' => {'일치' if td_number == search_number else '불일치'}")
            if td_number == search_number:
                print(f"[DEBUG] 일치 발견! 차량번호: '{result.text}'")
                found = True
                break
        
        if found:
            print(f"차량 {car_number_full} 입차 확인됨")
            return "entered"
        else:
            print(f"차량 {car_number_full} 검색 결과 없음(미입차 처리)")
            return "not_entered"
    except Exception as e:
        print(f"입차 확인 중 오류(상세): {e}")
        try:
            home_btn_right = wait.until(EC.element_to_be_clickable((By.ID, "headerHome")))
            home_btn_right.click()
        except Exception as e2:
            print(f"오른쪽 상단 홈 버튼 클릭 실패(입차 확인): {e2}")
        return "not_entered"

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
            return "error:팝업 처리 중 오류"
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
        return "error:탭 전체 오류"

# 차량번호 정규화 함수 (한글, 숫자만 남김)
def normalize_car_number(car_number):
    if not car_number:
        return ''
    only_kor_num = re.sub(r'[^가-힣0-9]', '', car_number)
    return only_kor_num.strip()

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

def is_discount_applied_3times(driver):
    # 모든 td 태그 중에서 텍스트가 '1시간(무료)'인 것만 카운트
    discount_items = driver.find_elements(By.TAG_NAME, "td")
    count = sum(1 for item in discount_items if item.text.strip() == "1시간(무료)")
    print(f"[DEBUG] '1시간(무료)' 할인권 적용 내역 개수: {count}")
    return count >= 3

def run_last_update_process():
    """Last Update 프로세스 실행 함수"""
    print("\n" + "="*50)
    print("=== Last Update 프로세스 시작 ===")
    print("="*50)
    print("1-2단계: 입차 여부 검사 및 리스트 생성")
    print("3-4단계: 주차권 등록 자동화")
    print("="*50)

    print("\n" + "="*50)
    print("=== 1단계: 입차 여부 검사 및 리스트 생성 ===")
    print("="*50)

    # 차량_DB 시트의 사본 접근
    try:
        db_worksheet = sh.worksheet('차량_DB 시트')
        print("차량_DB 시트 접근 완료")
    except Exception as e:
        print(f"차량_DB 시트 접근 실패: {e}")
        return

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
        
        # D열이 '입차' 상태인 차량은 재검색 없이 기존 값 유지
        if status == "입차":
            update_values.append([
                cycle_label,   # A: 회차
                name,          # B: 이름 (기존 값 유지)
                car_number,    # C: 차번호 (기존 값 유지)
                status,        # D: 입차 여부
                prev_time,     # E: 입차확인시간 (기존 값 유지)
                prev_time      # F: 실입차시간 (기존 값 유지)
            ])
            print(f"{car_number} - 이미 입차 확인됨, 재검색 건너뛰기")
            continue
        
        # 차량번호가 없는 경우 빈 칸으로 처리
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
        
        # 미입차 또는 빈 상태인 차량만 실제 검색 수행
        print(f"{car_number} - 입차 여부 확인 중... (이전 상태: {status if status else '빈칸'})")
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

    print("\n" + "="*50)
    print("=== 2단계: 입차 차량 리스트 생성 ===")
    print("="*50)

    # 업데이트된 데이터 다시 읽기
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

    print(f"\n입차 차량 총 {len(entered_rows)}대 발견")

    if len(entered_rows) == 0:
        print("입차된 차량이 없습니다.")
        return

    print("\n=== 입차 차량 목록 ===")
    for idx, (in_time, name, car_number) in enumerate(entered_rows, 1):
        print(f"{idx}. {car_number} ({name}) - 입차시간: {in_time}")

    print("\n" + "="*50)
    print("=== 3단계: 주차등록 차량 명단 시트에 복사 ===")
    print("="*50)

    try:
        parking_reg_worksheet = sh.worksheet('주차등록 차량 명단 시트')
        print("주차등록 차량 명단 시트 접근 완료")
        
        # 헤더 설정
        parking_reg_worksheet.update([['번호','입차 확인 시간','성도명', '차량번호', '상태', '처리 시간']], 'A1:F1')
        
        # 입차 차량 정보 복사 (2번째 줄부터)
        for idx, (in_time, name, car_number) in enumerate(entered_rows):
            parking_reg_worksheet.update_cell(idx + 2, 2, in_time)      # B열: 입차 확인 시간
            parking_reg_worksheet.update_cell(idx + 2, 3, name)         # C열: 성도명
            parking_reg_worksheet.update_cell(idx + 2, 4, car_number)   # D열: 차량번호
            print(f"{car_number} - 주차등록 차량 명단에 복사 완료")
        
        print("입차 차량 명단이 '주차등록 차량 명단 시트'에 기록되었습니다.")
    except Exception as e:
        print(f"'주차등록 차량 명단 시트' 기록 실패: {e}")
        return

    print("\n" + "="*50)
    print("=== 4단계: 주차권 등록 자동화 ===")
    print("="*50)

    # 주차권 등록 자동화
    car_numbers = parking_reg_worksheet.col_values(4)[1:]  # D열(차량번호), [1:]로 헤더 제외
    current_status = parking_reg_worksheet.col_values(5)[1:] if len(parking_reg_worksheet.col_values(5)) > 1 else []  # E열(상태)

    print(f"주차권 등록 대상: 총 {len(car_numbers)}대")

    success_count = 0
    fail_count = 0
    status_update = []  # 결과를 모을 리스트

    for idx, car_number in enumerate(car_numbers):
        if not car_number.strip():
            status_update.append(["", ""])
            continue
        
        # 현재 상태 확인 (E열)
        current_car_status = current_status[idx] if idx < len(current_status) else ""
        
        # 이미 "성공"인 차량은 재등록 없이 기존 값 유지
        if current_car_status == "성공":
            status_update.append([current_car_status, ""])  # 기존 상태 유지, 처리시간은 갱신하지 않음
            print(f"[{idx+1}/{len(car_numbers)}] {car_number} - 이미 성공 완료됨, 재등록 건너뛰기")
            success_count += 1
            continue
        
        # 빈칸, 실패 등인 차량만 실제 등록 수행
        print(f"\n[{idx+1}/{len(car_numbers)}] {car_number} - 주차권 등록 시작 (이전 상태: {current_car_status if current_car_status else '빈칸'})")
        tab_results = []
        
        # 3개 탭에서 순차적으로 등록 시도
        for tab_idx in range(len(handles)):
            driver.switch_to.window(handles[tab_idx])
            print(f"  {tab_idx+1}번째 탭에서 시도 중...")
            result = safe_apply_discount(driver, car_number)
            tab_results.append(result)
            print(f"  {tab_idx+1}번째 탭 결과: {result}")
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if all(r == "success" for r in tab_results) or is_discount_applied_3times(driver):
            status_update.append(["성공", now_str])
            print(f"  {car_number} - 최종 결과: 성공 (3개 탭 모두 성공 또는 할인권 3개 적용)")
            success_count += 1
        else:
            status_update.append(["실패 (오류 : 탭)", now_str])
            print(f"  {car_number} - 최종 결과: 실패 (하나 이상의 탭에서 실패)")
            fail_count += 1

    # === 여기서 한 번에 업데이트 ===
    if status_update:
        update_range = f'E2:F{len(car_numbers)+1}'
        parking_reg_worksheet.update(update_range, status_update)

    print("\n" + "="*50)
    print("=== Last Update 프로세스 완료 ===")
    print("="*50)
    print(f"입차 검사: 총 {processed_count}대 처리")
    print(f"입차 확인: {len(entered_rows)}대 발견")
    print(f"주차권 등록: 성공 {success_count}대, 실패 {fail_count}대")

def run_simple_logic_process():
    """Simple Logic 프로세스 실행 함수"""
    print(f"\n=== Simple Logic 프로세스 실행 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # QR로 등록된 차량 시트에서 차량번호 및 상태 읽기
    try:
        db_worksheet = sh.worksheet('Simple_bot')
        print("Simple_bot 시트 접근 완료")
        all_data = db_worksheet.get_all_values()[1:]  # 헤더 제외한 모든 데이터
        car_numbers = [row[2] if len(row) > 2 else "" for row in all_data]  # C열: 차량번호
        current_status = [row[3] if len(row) > 3 else "" for row in all_data]  # D열: 현재 상태
    except Exception as e:
        print(f"Simple_bot 시트 접근 실패: {e}")
        return

    status_update = []
    processed_count = 0  # 실제 처리한 차량 수
    
    for idx, car_number in enumerate(car_numbers):
        if not car_number.strip():
            status_update.append(["", ""])
            continue
        
        # 이미 처리된 차량은 건너뛰기 (D열에 내용이 있으면)
        if current_status[idx].strip():
            status_update.append([current_status[idx], ""])  # 기존 상태 유지
            print(f"[{idx+1}/{len(car_numbers)}] {car_number} - 이미 처리됨({current_status[idx]}), 건너뛰기")
            continue
        
        print(f"\n[{idx+1}/{len(car_numbers)}] {car_number} - 주차권 등록 시작")
        processed_count += 1
        tab_results = []
        for tab_idx in range(len(handles)):
            driver.switch_to.window(handles[tab_idx])
            print(f"  {tab_idx+1}번째 탭에서 시도 중...")
            result = safe_apply_discount(driver, car_number)
            tab_results.append(result)
            print(f"  {tab_idx+1}번째 탭 결과: {result}")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if all(r == "success" for r in tab_results):
            status_update.append(["성공", now_str])
            print(f"  {car_number} - 최종 결과: 성공 (모든 탭 성공)")
        else:
            # 실패 사유: 가장 먼저 발생한 실패 사유 1개만 간단히 표시
            fail_reason = next((r for r in tab_results if r != "success"), "알수없음")
            status_update.append([f"실패 ({fail_reason})", now_str])
            print(f"  {car_number} - 최종 결과: 실패 ({fail_reason})")

    # 결과를 구글 시트에 기록 (D, E열: 상태/처리시간)
    try:
        db_worksheet.update(f'D2:E{len(car_numbers)+1}', status_update)
        print("구글 시트에 결과 기록 완료")
    except Exception as e:
        print(f"구글 시트 결과 기록 실패: {e}")

    print(f"=== Simple Logic 프로세스 완료 - 처리한 차량: {processed_count}대 ===")

def check_browser_connection():
    """브라우저 연결 상태 확인 및 재연결"""
    global driver, handles
    try:
        # 현재 창 제목을 확인해서 연결 상태 테스트
        driver.title
        handles = driver.window_handles
        if len(handles) == 0:
            raise Exception("탭이 없습니다")
        return True
    except Exception as e:
        print(f"브라우저 연결 끊김 감지: {e}")
        try:
            # 재연결 시도
            options = webdriver.ChromeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)
            handles = driver.window_handles
            print(f"브라우저 재연결 성공. 탭 개수: {len(handles)}")
            return True
        except Exception as e2:
            print(f"브라우저 재연결 실패: {e2}")
            return False

def safe_apply_discount(driver, car_number):
    """안전한 할인 적용 함수 - 오류 처리 강화"""
    try:
        # 브라우저 연결 상태 확인
        if not check_browser_connection():
            return "error:브라우저 연결 실패"
        
        return apply_discount(driver, car_number)
    except Exception as e:
        error_msg = str(e)
        print(f"할인 적용 중 오류: {error_msg}")
        
        # 일반적인 오류 메시지로 간소화
        if "Stacktrace:" in error_msg or "GetHandleVerifier" in error_msg:
            return "error:브라우저 오류"
        elif "no such element" in error_msg.lower():
            return "error:요소 찾기 실패"
        elif "timeout" in error_msg.lower():
            return "error:시간 초과"
        else:
            return "error:알수없는 오류"

def start_chrome_debug_mode():
    # 크롬 디버깅 모드 실행 명령어
    chrome_command = r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_temp"'
    subprocess.Popen(chrome_command, shell=True)
    print("크롬 디버깅 모드 시작")
    time.sleep(1)  # 크롬이 완전히 열릴 때까지 1초 대기

def open_tabs_and_load_url(driver, url):
    # 현재 열려 있는 탭 수 확인
    current_tabs = len(driver.window_handles)
    # 필요한 탭 수 계산
    tabs_to_open = 3 - current_tabs

    # 부족한 탭 수만큼 열기
    for _ in range(tabs_to_open):
        driver.execute_script("window.open('');")
    handles = driver.window_handles[:3]  # 최대 3개의 탭만 사용

    for i, handle in enumerate(handles):
        driver.switch_to.window(handle)
        driver.get(url)
        print(f"탭 {i+1}에서 {url} 페이지로 이동")
    
    return handles

def is_logged_in(driver):
    try:
        # 로그인 여부를 확인할 수 있는 요소를 찾습니다.
        # 예: 로그인 후에만 보이는 특정 요소
        driver.find_element(By.ID, "logout")  # 로그아웃 버튼의 ID
        return True
    except:
        return False

def login_to_site(driver, username, password):
    if not is_logged_in(driver):
        try:
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "id"))
            )
            password_input = driver.find_element(By.ID, "password")
            login_button = driver.find_element(By.ID, "login")

            username_input.send_keys(username)
            password_input.send_keys(password)
            login_button.click()
            print("로그인 완료")
        except Exception as e:
            print(f"로그인 실패: {e}")
    else:
        print("이미 로그인된 상태입니다.")

def main():
    """메인 함수: 두 프로세스를 순차적으로 실행"""
    print("=== iParking 통합 자동화 프로그램 시작 ===")
    print("Last Update + Simple Logic 순차 실행")
    print("="*50)

    # 크롬 디버깅 모드 시작
    start_chrome_debug_mode()

    # 이미 로그인된 크롬 세션에 연결
    global driver, sh
    try:
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=options)
        print(f"크롬 브라우저 연결 완료.")
    except Exception as e:
        print(f"크롬 브라우저 연결 실패: {e}")
        exit()

    # 3개의 탭 열고 로그인 페이지 로드
    login_url = "http://members.iparking.co.kr/html/login.html#!"
    handles = open_tabs_and_load_url(driver, login_url)

    # 각 탭에서 로그인 수행
    credentials = [
        {"username": "dreamcb01", "password": "dreamcb01"},
        {"username": "dreamcb02", "password": "dreamcb02"},
        {"username": "dreamcb03", "password": "dreamcb03"}
    ]

    for i, handle in enumerate(handles):
        if i < len(credentials):  # credentials 리스트의 길이에 맞춰 로그인
            driver.switch_to.window(handle)
            login_to_site(driver, credentials[i]["username"], credentials[i]["password"])

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

    print("300초(5분)마다 통합 자동화 실행을 시작합니다...")
    print("프로그램을 중단하려면 Ctrl+C를 누르세요.")

    # 300초마다 반복 실행
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"\n{'='*70}")
            print(f"통합 사이클 {cycle_count} 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")
            
            # Last Update 프로세스 실행
            try:
                run_last_update_process()
            except Exception as e:
                print(f"Last Update 프로세스 오류: {e}")
            
            print("\n" + "="*50)
            print("=== 프로세스 간 대기 (10초) ===")
            print("="*50)
            time.sleep(10)  # 프로세스 간 10초 대기
            
            # Simple Logic 프로세스 실행
            try:
                run_simple_logic_process()
            except Exception as e:
                print(f"Simple Logic 프로세스 오류: {e}")
            
            print(f"\n{'='*70}")
            print(f"통합 사이클 {cycle_count} 완료")
            print(f"다음 실행까지 300초(5분) 대기 중...")
            print(f"다음 실행 예정 시간: {(datetime.now() + timedelta(seconds=300)).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")
            
            # 300초 대기
            time.sleep(300)
            
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
        print("=== iParking 통합 자동화 프로그램 종료 ===")

if __name__ == "__main__":
    main()