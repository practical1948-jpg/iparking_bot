# & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_temp"
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 구글 스프레드시트 API 인증
logging.debug('Google Sheets API 인증 시작')
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('Rpr_cross-validation.json', scope)
client = gspread.authorize(creds)
logging.debug('Google Sheets API 인증 완료')

# 스프레드시트 열기
logging.debug('스프레드시트 열기 시도')
spreadsheet = client.open("PLC_정기 주차 등록")
worksheet = spreadsheet.worksheet("PLC_정기 주차 등록 DB")  # 실제 시트 이름을 사용
logging.debug('스프레드시트 열기 완료')

# 데이터 읽기
logging.debug('데이터 읽기 시도')
expected_headers = ["신청 시간", "이름", "차량번호", "전화번호", "교인 여부"]
data = worksheet.get_all_records(expected_headers=expected_headers)
logging.debug('데이터 읽기 완료')
print(data)
