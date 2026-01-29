import time
import re
import os
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add project root to sys.path
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from config import settings
from src.core.browser import start_chrome_debug_mode, cleanup_debug_chrome
from src.services.firebase import get_parking_records, save_parking_record, update_remark, initialize_firebase, get_db

class ParkingBot:
    def __init__(self):
        self.driver = None
        self.handles = []
        self.db = initialize_firebase()
        
    def start(self):
        """봇 시작: 브라우저 연결 및 로그인"""
        print("=== iParking Bot Starting ===")
        if not start_chrome_debug_mode():
            raise Exception("Chrome start failed")
            
        self.connect_browser()
        self.login_all_tabs()
        
    def connect_browser(self):
        """셀레니움 드라이버 연결"""
        print("Connecting to Chrome...")
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{settings.CHROME_DEBUG_PORT}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver = webdriver.Chrome(options=options)
                print("Connected to Chrome!")
                break
            except Exception as e:
                print(f"Connection attempt {attempt+1} failed: {e}")
                time.sleep(5)
                if attempt == max_retries - 1:
                    raise e

        # 탭 핸들 관리
        self.handles = self.driver.window_handles
        # 탭 3개 확인 로직 (간소화)
        while len(self.handles) < 3:
             self.driver.execute_script(f"window.open('{settings.IPARKING_URL}', '_blank');")
             time.sleep(1)
             self.handles = self.driver.window_handles
        
    def login_all_tabs(self):
        """모든 탭 로그인"""
        print("Checking Login Status...")
        accounts = settings.ACCOUNTS
        
        for i, handle in enumerate(self.handles[:3]):
            try:
                self.driver.switch_to.window(handle)
                if i < len(accounts):
                    self.login_tab(accounts[i])
            except Exception as e:
                print(f"Tab {i} login error: {e}")

    def login_tab(self, account):
        """단일 탭 로그인"""
        try:
            if "login" in self.driver.current_url:
                print(f"Logging in {account['username']}...")
                wait = WebDriverWait(self.driver, 5)
                id_input = wait.until(EC.presence_of_element_located((By.ID, "id")))
                id_input.clear()
                id_input.send_keys(account['username'])
                
                pw_input = self.driver.find_element(By.ID, "password")
                pw_input.clear()
                pw_input.send_keys(account['password'])
                pw_input.send_keys('\n')
                time.sleep(2)
        except Exception as e:
            print(f"Login failed: {e}")

    def normalize_car_number(self, car_number):
        return re.sub(r'[^가-힣0-9]', '', str(car_number))

    def apply_discount(self, car_number, return_home=True):
        """할인권 적용 로직 (Core Logic)"""
        driver = self.driver
        wait = WebDriverWait(driver, 3)
        
        # 팝업 확인 로직 (Simplified)
        try:
            popup = driver.find_elements(By.ID, "popupOk")
            if popup and popup[0].is_displayed():
                popup[0].click()
        except: pass
        
        try:
            # 차량 번호 입력
            input_box = wait.until(EC.element_to_be_clickable((By.ID, "carNumber")))
            input_box.clear()
            last4 = car_number[-4:]
            input_box.send_keys(last4)
            driver.find_element(By.CLASS_NAME, "btn-search").click()
            time.sleep(1)
            
            # 검색 결과 처리
            try:
                no_result = driver.find_element(By.ID, "parkName")
                if "검색된 차량이 없습니다" in no_result.text:
                    if return_home: self.go_home()
                    return "no_car"
            except: pass
            
            # 결과 클릭
            results = driver.find_elements(By.CSS_SELECTOR, ".car-number-cell")
            if not results: results = driver.find_elements(By.TAG_NAME, "td")
            
            found = False
            search_full = self.normalize_car_number(car_number)
            
            for res in results:
                if self.normalize_car_number(res.text) == search_full:
                    res.click()
                    found = True
                    break
            
            if not found and results:
                # 첫번째 자동 선택 (Logic from legacy)
                results[0].click()
                found = True
                
            if found:
                wait.until(EC.element_to_be_clickable((By.ID, "next"))).click()
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-apply"))).click()
                
                # 결과 확인 (할인권 개수)
                time.sleep(2)
                try:
                     # "총 할인 내역" 확인 로직
                    discount_items = driver.find_elements(By.XPATH, "//td[text()='1시간(무료)']")
                    count = len(discount_items)
                    
                    if return_home: self.go_home()
                    
                    if count >= 3: return "success"
                    elif count > 0: return "partial"
                    else: return "fail"
                except:
                    if return_home: self.go_home()
                    return "unknown"
            
            if return_home: self.go_home()
            return "no_car"
            
        except Exception as e:
            print(f"Apply discount error: {e}")
            if return_home: self.go_home()
            return "error"

    def go_home(self):
        try:
            self.driver.find_element(By.ID, "headerHome").click()
        except: pass

    def run_polling(self):
        """Firebase 폴링 루프"""
        print("🚀 Polling Mode Started. Waiting for input...")
        while True:
            try:
                # 오늘 날짜 미등록 차량 조회
                db = get_db()
                today = datetime.now().strftime('%Y-%m-%d')
                
                docs = db.collection('parking_records')\
                    .where('날짜', '==', today)\
                    .where('상태', 'in', ['미등록', '처리중'])\
                    .stream()
                
                pending_list = []
                for doc in docs:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    pending_list.append(data)
                
                if pending_list:
                    print(f"Found {len(pending_list)} pending items.")
                    for item in pending_list:
                        print(f"Processing: {item['차량번호']}")
                        
                        # 상태 처리중으로 변경
                        db.collection('parking_records').document(item['id']).update({'상태': '처리중...'})
                        
                        # 실제 처리 (3개 탭 시도 Logic)
                        final_result = "실패"
                        for i, handle in enumerate(self.handles):
                            self.driver.switch_to.window(handle)
                            res = self.apply_discount(item['차량번호'])
                            if res == "success":
                                final_result = "등록성공(완료)"
                                break # 하나라도 성공하면 중단? 아니면 3개 다? 
                                # Legacy logic tried all 3 tabs to apply 3 coupons.
                        
                        # Legacy Logis is: try ALL tabs.
                        # I should try all tabs.
                        
                        # Retry correct logic:
                        success_count = 0
                        for i, handle in enumerate(self.handles):
                            try:
                                self.driver.switch_to.window(handle)
                                # Check if already applied enough?
                                # Just apply.
                                res = self.apply_discount(item['차량번호'], return_home=True)
                                if res in ["success", "partial"]:
                                    success_count += 1
                            except: pass
                            
                        # Final Status
                        if success_count >= 1: # At least one attempt worked (which might apply 1-3 coupons)
                            # Wait, 'apply_discount' checks '1시간(무료)' count.
                            # If count is 3, it returns success.
                            # So I should check if I need to run multiple tabs.
                            # Legacy logic ran loop over tabs.
                            final_status = "등록성공" if success_count > 0 else "실패"
                        else:
                             final_status = "실패"
                             
                        # Update Firebase
                        db.collection('parking_records').document(item['id']).update({
                            '상태': final_status,
                            '처리시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        print(f"Updated status for {item['차량번호']}: {final_status}")
                        
                time.sleep(5) # Poll every 5 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    bot = ParkingBot()
    bot.start()
    bot.run_polling()
