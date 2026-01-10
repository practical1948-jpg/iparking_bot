# iParking 주차권 등록 실시간 대시보드
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from datetime import datetime, timedelta
import re
import time
import glob
import shutil
import json
import hashlib
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Firebase 연동
try:
    from firebase_helper import get_parking_records, initialize_firebase, update_remark
    FIREBASE_IMPORT_SUCCESS = True
except ImportError as e:
    FIREBASE_IMPORT_SUCCESS = False
    print(f"⚠️ Firebase 모듈 import 실패: {e}")

# 자동 새로고침 컴포넌트 임포트 (설치: pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
    AUTO_REFRESH_AVAILABLE = True
except ImportError:
    AUTO_REFRESH_AVAILABLE = False
    print("⚠️ streamlit-autorefresh 모듈이 설치되지 않았습니다. 'pip install streamlit-autorefresh'로 설치하세요.")

# 페이지 설정
st.set_page_config(
    page_title="iParking 자동등록 시스템",
    page_icon="🚗",
    layout="wide"
)

# 자동 새로고침 설정 (선택 가능)
# 사이드바에서 자동 새로고침 ON/OFF 선택
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = True  # 기본값 True로 변경

# 자동 새로고침이 활성화되어 있을 때만 실행
if AUTO_REFRESH_AVAILABLE and st.session_state.auto_refresh_enabled:
    # 10000ms = 10초마다 자동 새로고침
    st_autorefresh(interval=10000, key="datarefresh")

# CSS 스타일 추가 (텍스트 색상 개선 및 섹션 간격 조정)
st.markdown("""
<style>
    /* 텍스트 색상 명확하게 설정 */
    .stMarkdown, .stText, p, div {
        color: #ffffff !important;
    }
    
    /* 테이블 텍스트 색상 */
    .dataframe {
        color: #ffffff !important;
    }
    
    /* 강조 텍스트 */
    strong {
        color: #ffffff !important;
        font-weight: bold;
    }
    
    /* 섹션 간격 조정 */
    .element-container {
        margin-bottom: 1.5rem;
    }
    
    /* 제목 간격 */
    h1, h2, h3 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    
    /* 통계 카드 통일 */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 제목
st.title("🚗 iParking 주차권 자동등록 시스템")

# 스크롤 위치 저장 및 복원 JavaScript
scroll_script = """
<script>
    // 페이지 로드 시 저장된 스크롤 위치로 복원
    window.addEventListener('load', function() {
        const scrollPos = sessionStorage.getItem('scrollPosition');
        if (scrollPos) {
            window.scrollTo(0, parseInt(scrollPos));
        }
    });
    
    // 스크롤 위치를 주기적으로 저장
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(function() {
            sessionStorage.setItem('scrollPosition', window.scrollY);
        }, 100);
    });
    
    // 페이지를 떠나기 전에 스크롤 위치 저장
    window.addEventListener('beforeunload', function() {
        sessionStorage.setItem('scrollPosition', window.scrollY);
    });
</script>
"""
components.html(scroll_script, height=0)

# Firebase 초기화
if FIREBASE_IMPORT_SUCCESS:
    try:
        db = initialize_firebase()
        if db:
            FIREBASE_AVAILABLE = True
            st.sidebar.success("🔥 Firebase 연결됨")
        else:
            FIREBASE_AVAILABLE = False
            st.sidebar.error("⚠️ Firebase 연결 실패")
            st.sidebar.caption("Firebase 초기화 실패 (DB 없음)")
    except Exception as e:
        FIREBASE_AVAILABLE = False
        st.sidebar.error("⚠️ Firebase 연결 실패")
        st.sidebar.caption(f"에러: {str(e)}")
        print(f"Firebase 초기화 에러: {e}")
else:
    FIREBASE_AVAILABLE = False
    st.sidebar.warning("⚠️ Firebase 모듈 없음")

# CSV 파일 경로 (상대 경로 사용 - 배포 가능)
# 현재 스크립트 파일의 위치를 기준으로 상위 디렉토리 사용
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.dirname(SCRIPT_DIR)  # iparking-bot 폴더의 상위 디렉토리
DB_FOLDER = os.path.join(BASE_PATH, "주차_DB_파일")
EXECUTION_LOG_PATH = os.path.join(BASE_PATH, "file_execution_log.json")

# 주차 DB 폴더 생성 (없으면)
os.makedirs(DB_FOLDER, exist_ok=True)

def load_execution_log():
    """파일 실행 이력 로드"""
    try:
        if os.path.exists(EXECUTION_LOG_PATH):
            with open(EXECUTION_LOG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f).get("execution_history", {})
        return {}
    except Exception as e:
        print(f"로그 로드 실패: {e}")
        return {}

def get_latest_db_file():
    """주차_DB_파일 폴더에서 가장 최근 CSV 파일을 찾음"""
    try:
        csv_files = glob.glob(os.path.join(DB_FOLDER, "*.csv"))
        if not csv_files:
            return None
        return max(csv_files, key=os.path.getmtime)
    except Exception as e:
        print(f"최신 파일 검색 오류: {e}")
        return None

# 설문지 응답 파일 경로
DAILY_CSV_PATH_DEFAULT = os.path.join(BASE_PATH, "(신규)주차등록(응답) - 설문지 응답 시트1.csv")

# 기본 파일 찾기
DEFAULT_DB_CSV = get_latest_db_file() or ""
DEFAULT_DAILY_CSV = DAILY_CSV_PATH_DEFAULT if os.path.exists(DAILY_CSV_PATH_DEFAULT) else ""

# 사이드바에서 파일 관리
st.sidebar.header("⚙️ 설정")

# 자동 새로고침 설정
st.sidebar.subheader("🔄 자동 새로고침")
auto_refresh = st.sidebar.checkbox(
    "자동 새로고침 활성화",
    value=st.session_state.auto_refresh_enabled,
    help="체크하면 10초마다 자동으로 데이터를 새로고침합니다"
)
if auto_refresh != st.session_state.auto_refresh_enabled:
    st.session_state.auto_refresh_enabled = auto_refresh
    st.rerun()

if st.session_state.auto_refresh_enabled:
    st.sidebar.caption("⏱️ 10초마다 자동 새로고침 중")
else:
    st.sidebar.caption("🔄 수동 새로고침 모드")

st.sidebar.markdown("---")

# 📤 CSV 파일 업로드 섹션
st.sidebar.subheader("📤 CSV 파일 업로드")
uploaded_file = st.sidebar.file_uploader(
    "주차 DB CSV 파일",
    type=['csv'],
    help="파일을 업로드하면 주차_DB_파일 폴더에 자동 저장됩니다",
    key="db_file_uploader"
)

if uploaded_file is not None:
    # 주차_DB_파일 폴더에 저장
    save_path = os.path.join(DB_FOLDER, uploaded_file.name)
    try:
        with open(save_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"✅ 파일 저장 완료!")
        st.sidebar.caption(f"📁 {uploaded_file.name}")
        # 페이지 새로고침으로 최신 파일 반영
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 파일 저장 실패: {e}")

st.sidebar.markdown("---")

# 📂 현재 파일 목록 표시
st.sidebar.subheader("📂 주차_DB_파일 목록")
db_files = glob.glob(os.path.join(DB_FOLDER, "*.csv"))
execution_log = load_execution_log()

if db_files:
    # 최신 순으로 정렬
    db_files.sort(key=os.path.getmtime, reverse=True)
    
    latest_file = db_files[0]
    file_name = os.path.basename(latest_file)
    file_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
    
    st.sidebar.success(f"✅ 사용 중: {file_name}")
    st.sidebar.caption(f"📅 파일 수정: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 실행 이력 표시
    if file_name in execution_log:
        last_exec = execution_log[file_name].get("last_executed", "기록 없음")
        exec_count = execution_log[file_name].get("execution_count", 0)
        st.sidebar.caption(f"🚀 마지막 실행: {last_exec}")
        st.sidebar.caption(f"📊 실행 횟수: {exec_count}회")
    else:
        st.sidebar.caption(f"🚀 마지막 실행: 기록 없음")
    
    # 나머지 파일 목록
    if len(db_files) > 1:
        with st.sidebar.expander(f"📋 다른 파일 ({len(db_files)-1}개)"):
            for file_path in db_files[1:]:
                file_name = os.path.basename(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                st.caption(f"📄 {file_name}")
                st.caption(f"   수정: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 실행 이력
                if file_name in execution_log:
                    last_exec = execution_log[file_name].get("last_executed", "-")
                    st.caption(f"   실행: {last_exec}")
else:
    st.sidebar.warning("⚠️ 주차_DB_파일 폴더가 비어있습니다")
    st.sidebar.caption("위에서 CSV 파일을 업로드하세요")

st.sidebar.markdown("---")

# 파일 경로 자동 설정
DB_CSV_PATH = get_latest_db_file() or ""
DAILY_CSV_PATH = DAILY_CSV_PATH_DEFAULT

# 파일 존재 여부 표시
st.sidebar.subheader("📊 파일 상태")
db_exists = DB_CSV_PATH and os.path.exists(DB_CSV_PATH)
daily_exists = os.path.exists(DAILY_CSV_PATH)

st.sidebar.markdown(f"차량_DB: {'✅ 존재' if db_exists else '❌ 없음'}")
st.sidebar.markdown("---")

# 파일 수정 시간 가져오기 함수
def get_file_mtime(csv_path):
    """파일의 수정 시간을 반환 (캐시 키로 사용)"""
    if os.path.exists(csv_path):
        return os.path.getmtime(csv_path)
    return None

# 데이터 로드 함수 (파일 수정 시간을 캐시 키에 포함)
@st.cache_data(ttl=3)  # 3초마다 캐시 체크
def load_data_from_firebase(date_str=None):
    """
    Firebase에서 실시간 데이터 로드
    """
    try:
        # Firebase에서 데이터 가져오기
        records = get_parking_records(date_str)
        
        if not records:
            return None
        
        # DataFrame으로 변환
        df = pd.DataFrame(records)
        
        # 필요한 컬럼 순서 정렬 (번호 제거, 비고 추가)
        column_order = ['회차', '성함', '차량번호', '상태', '처리시간', '데이터소스', '비고', '번호']
        existing_cols = [col for col in column_order if col in df.columns]
        df = df[existing_cols]
        
        # 비고 컬럼이 없으면 추가
        if '비고' not in df.columns:
            df['비고'] = ''
        
        return df
        
    except Exception as e:
        st.error(f"Firebase 데이터 로드 오류: {e}")
        return None

@st.cache_data(ttl=3)  # 3초마다 캐시 체크
def load_data(csv_path, file_mtime):
    """
    파일 수정 시간(file_mtime)이 변경되면 자동으로 새로운 데이터를 로드
    로컬 환경에서만 사용 (백업용)
    """
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            # 열 이름 정규화
            df.columns = df.columns.str.replace('\n', ' ').str.strip()
            return df
        except Exception as e:
            st.error(f"CSV 파일 읽기 오류: {e}")
            return None
    return None

# 날짜 추출 함수
def extract_date_from_row(row):
    """행에서 날짜 추출 (타임스탬프 또는 처리시간)"""
    # 처리시간 컬럼 확인
    if '처리시간' in row and pd.notna(row['처리시간']) and str(row['처리시간']).strip():
        try:
            date_str = str(row['처리시간']).strip()
            # "2025-12-10 11:07:05" 형식 파싱
            if len(date_str) >= 10:
                return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        except:
            pass
    
    # 타임스탬프 컬럼 확인
    if '타임스탬프' in row and pd.notna(row['타임스탬프']):
        try:
            timestamp_str = str(row['타임스탬프']).strip()
            # "2025. 12. 10 오전 11:07:05" 형식 파싱
            date_match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', timestamp_str)
            if date_match:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day)).date()
        except:
            pass
    
    # 날짜를 찾을 수 없으면 오늘 날짜 반환
    return datetime.now().date()


def render_sidebar(data_name: str, date_info: str, df: pd.DataFrame, csv_path: str, is_all_mode: bool = False):
    """오른쪽에 항상 보이는 깔끔한 사이드바 렌더링"""
    # 자동 새로고침 안내
    if AUTO_REFRESH_AVAILABLE:
        st.sidebar.success("✅ 5초마다 자동 새로고침 활성화")
    else:
        st.sidebar.warning("⚠️ 자동 새로고침 비활성화")
        st.sidebar.caption("💡 설치: pip install streamlit-autorefresh")
    st.sidebar.caption(f"🕐 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 캐시 새로고침 버튼 (탭별로 key를 달리해서 DuplicateElementId 방지)
    if st.sidebar.button("🔄 캐시 새로고침", key=f"refresh_cache_{data_name}"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    # 현재 데이터 정보
    st.sidebar.write("**현재 데이터**")
    st.sidebar.success(f"📊 {data_name}")
    st.sidebar.caption(f"📅 {date_info}")

    st.sidebar.markdown("---")

    # CSV / 파일 정보
    st.sidebar.write("**데이터 소스**")

    if is_all_mode:
        # 통합 모드: 주차명단 + 수동입력
        st.sidebar.caption(f"📊 주차명단: {os.path.basename(DB_CSV_PATH)}")
        st.sidebar.caption(f"📝 일일등록: {os.path.basename(DAILY_CSV_PATH)}")

        db_exists = os.path.exists(DB_CSV_PATH)
        daily_exists = os.path.exists(DAILY_CSV_PATH)

        if db_exists and daily_exists:
            st.sidebar.success("✅ 두 파일 모두 존재")
            db_time = datetime.fromtimestamp(os.path.getmtime(DB_CSV_PATH))
            daily_time = datetime.fromtimestamp(os.path.getmtime(DAILY_CSV_PATH))
            st.sidebar.caption(f"📝 주차명단 수정: {db_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.sidebar.caption(f"📝 일일등록 수정: {daily_time.strftime('%Y-%m-%d %H:%M:%S')}")
        elif db_exists:
            st.sidebar.warning("⚠️ 주차명단만 존재")
        elif daily_exists:
            st.sidebar.warning("⚠️ 일일등록만 존재")
        else:
            st.sidebar.error("❌ 파일 없음")

        st.sidebar.caption(f"📊 통합 데이터: {len(df)}개 행")
    else:
        # 단일 CSV 모드
        filename = os.path.basename(csv_path) if csv_path else "-"
        st.sidebar.caption(filename)

        if csv_path and os.path.exists(csv_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(csv_path))
            st.sidebar.success("✅ 파일 존재")
            st.sidebar.caption(f"📝 수정 시간: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.sidebar.caption(f"📊 데이터: {len(df)}개 행")
        else:
            st.sidebar.error("❌ 파일 없음")

# 데이터 타입 선택을 탭 형식으로 변경
tab_db, tab_manual, tab_all = st.tabs(["📊 주차 명단", "✍️ 수동 입력", "🔗 전체"])

# 각 탭별 데이터 처리 함수
def render_data_tab(df, data_name, csv_path, is_all_mode=False):
    """각 탭의 데이터를 렌더링하는 함수"""
    if df is None or len(df) == 0:
        # Firebase 연결 상태에 따라 다른 메시지 표시
        if FIREBASE_AVAILABLE:
            # Firebase 연결 성공했지만 데이터 없음
            if data_name == "수동 입력":
                st.info("ℹ️ 수동 입력 데이터가 없습니다.")
                st.caption("💡 봇을 실행하고 '수동 입력 모드'로 차량을 등록하면 여기에 표시됩니다.")
            else:
                st.warning(f"❌ {data_name} 데이터가 없습니다.")
                st.caption(f"오늘({datetime.now().strftime('%Y-%m-%d')}) 처리된 데이터가 없습니다.")
        else:
            # Firebase 연결 실패
            st.error(f"⚠️ Firebase 연결 실패: {data_name} 데이터를 불러올 수 없습니다.")
            st.caption("Firebase 연결을 확인하거나 CSV 파일을 업로드하세요.")
        return
    
    # 디버깅 정보 (접을 수 있게)
    with st.expander("🔍 디버깅 정보", expanded=False):
        if is_all_mode:
            st.write(f"**주차명단 CSV 파일:** {DB_CSV_PATH}")
            st.write(f"**주차명단 파일 존재:** {'✅ 있음' if os.path.exists(DB_CSV_PATH) else '❌ 없음'}")
            if os.path.exists(DB_CSV_PATH):
                file_time = datetime.fromtimestamp(os.path.getmtime(DB_CSV_PATH))
                st.write(f"**주차명단 파일 수정 시간:** {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            st.write(f"**일일등록 CSV 파일:** {DAILY_CSV_PATH}")
            st.write(f"**일일등록 파일 존재:** {'✅ 있음' if os.path.exists(DAILY_CSV_PATH) else '❌ 없음'}")
            if os.path.exists(DAILY_CSV_PATH):
                file_time = datetime.fromtimestamp(os.path.getmtime(DAILY_CSV_PATH))
                st.write(f"**일일등록 파일 수정 시간:** {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.write(f"**CSV 파일 경로:** {csv_path}")
            st.write(f"**파일 존재:** {'✅ 있음' if os.path.exists(csv_path) else '❌ 없음'}")
            if os.path.exists(csv_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(csv_path))
                st.write(f"**파일 수정 시간:** {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        st.write(f"**데이터 행 수:** {len(df)}개")
        st.write(f"**컬럼:** {', '.join(df.columns.tolist())}")
    
    # 날짜 필터 추가
    st.subheader(f"📅 {data_name} 현황")
    
    # 날짜 선택 (달력)
    today = datetime.now().date()
    selected_date = st.date_input(
        "날짜 선택",
        value=today,
        help="조회할 날짜를 선택하세요",
        key=f"date_{data_name}"  # 각 탭별로 독립적인 키
    )
    
    # 날짜 기준으로 데이터 필터링
    df['날짜'] = df.apply(extract_date_from_row, axis=1)
    
    if data_name == "주차 명단":
        # 주차 명단: 선택한 날짜 처리된 차량 + 미처리 차량
        date_processed = df[df['날짜'] == selected_date]
        not_processed = df[(df['상태'] == '미등록') | (df['처리시간'].isna()) | (df['처리시간'] == '')]
        combined = pd.concat([date_processed, not_processed])
        filtered_df = combined.drop_duplicates(subset=df.columns.tolist()).reset_index(drop=True).copy()
        date_info = f"{selected_date.strftime('%Y년 %m월 %d일')} (처리 + 미처리)"
    elif is_all_mode:
        # 전체: 선택한 날짜 처리된 모든 데이터 (주차명단 + 수동입력)
        filtered_df = df[df['날짜'] == selected_date].copy()
        date_info = f"{selected_date.strftime('%Y년 %m월 %d일')} (전체)"
    else:
        # 수동 입력: 선택한 날짜 처리된 것만
        filtered_df = df[df['날짜'] == selected_date].copy()
        date_info = f"{selected_date.strftime('%Y년 %m월 %d일')}"
    
    # 상단 통계 (필터링된 데이터 기준) - 통일된 형식
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    total = len(filtered_df)
    success = len(filtered_df[filtered_df['상태'].str.contains('등록성공', na=False)]) if '상태' in filtered_df.columns else 0
    partial = len(filtered_df[filtered_df['상태'].str.contains('부분성공', na=False)]) if '상태' in filtered_df.columns else 0
    fail = len(filtered_df[filtered_df['상태'].str.contains('실패', na=False)]) if '상태' in filtered_df.columns else 0
    no_car = len(filtered_df[filtered_df['상태'].str.contains('차량 없음', na=False)]) if '상태' in filtered_df.columns else 0
    pending = len(filtered_df[filtered_df['상태'] == '미등록']) if '상태' in filtered_df.columns else total
    
    # 통일된 형식으로 표시
    col1.metric("📊 총 차량", f"{total}대")
    col2.metric("✅ 등록 성공", f"{success}대")
    col3.metric("⚠️ 부분 성공", f"{partial}대")
    col4.metric("❌ 등록 실패", f"{fail}대")
    col5.metric("🚫 차량 없음", f"{no_car}대")
    col6.metric("⏳ 대기 중", f"{pending}대")
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📋 전체 현황", "🔍 차량 조회", "📊 통계"])
    
    with tab1:
        st.subheader("전체 등록 현황")
        
        # 상태 필터
        status_filter_option = st.selectbox(
            "상태 필터",
            ["전체", "등록 성공", "부분 성공", "등록 실패", "차량 없음", "대기중"],
            key=f"status_filter_{data_name}"
        )
        
        # "미등록" → "대기중"으로 표시 변환
        filtered_df_display = filtered_df.copy()
        if '상태' in filtered_df_display.columns:
            filtered_df_display['상태'] = filtered_df_display['상태'].replace('미등록', '대기중')
        
        # 상태 필터 적용
        display_df = filtered_df_display.copy()
        if status_filter_option == "등록 성공":
            display_df = display_df[display_df['상태'].str.contains('등록성공', na=False)]
        elif status_filter_option == "부분 성공":
            display_df = display_df[display_df['상태'].str.contains('부분성공', na=False)]
        elif status_filter_option == "등록 실패":
            display_df = display_df[display_df['상태'].str.contains('실패', na=False)]
        elif status_filter_option == "차량 없음":
            display_df = display_df[display_df['상태'].str.contains('차량 없음', na=False)]
        elif status_filter_option == "대기중":
            display_df = display_df[display_df['상태'] == '대기중']
        
        # 날짜 컬럼 제거 (표시용)
        display_df_display = display_df.drop(columns=['날짜'], errors='ignore').copy()
        
        # 비고 컬럼을 문자열로 변환
        if '비고' in display_df_display.columns:
            display_df_display['비고'] = display_df_display['비고'].fillna('').astype(str)
            # 'nan' 문자열을 빈 문자열로 변환
            display_df_display['비고'] = display_df_display['비고'].replace('nan', '')
        
        # 회차 컬럼 순서 조정 및 정수 변환
        if '회차' in display_df_display.columns:
            # 회차를 정수로 변환 (빈 값은 빈 문자열로)
            def format_round(val):
                if pd.isna(val) or str(val).strip() == '':
                    return ''
                try:
                    return int(float(val))
                except:
                    return val
            
            display_df_display['회차'] = display_df_display['회차'].apply(format_round)
            
            cols = display_df_display.columns.tolist()
            cols.remove('회차')
            cols.insert(0, '회차')
            display_df_display = display_df_display[cols]
        
        # 전체 모드일 때 데이터 소스 컬럼 표시
        if is_all_mode and '데이터_소스' in display_df_display.columns:
            # 데이터 소스 컬럼을 앞으로 이동
            cols = display_df_display.columns.tolist()
            if '데이터_소스' in cols:
                cols.remove('데이터_소스')
                cols.insert(1 if '회차' in cols else 0, '데이터_소스')  # 회차 다음에 배치
                display_df_display = display_df_display[cols]
            display_df_display = display_df_display.rename(columns={'데이터_소스': '데이터 소스'})
        
        # 상태 컬럼에 아이콘 추가
        if '상태' in display_df_display.columns:
            def format_status(status):
                status_str = str(status)
                if '등록성공' in status_str:
                    return f"✅ {status_str}"
                elif '부분성공' in status_str:
                    return f"⚠️ {status_str}"
                elif '차량 없음' in status_str:
                    return f"🚫 {status_str}"
                elif '실패' in status_str:
                    return f"❌ {status_str}"
                elif status_str == '대기중':
                    return f"⏳ {status_str}"
                return status_str
            
            display_df_display['상태'] = display_df_display['상태'].apply(format_status)
        
        # 테이블 표시 (상태 컬럼에만 배경색 적용, 회차 컬럼에 흑백 체크무늬)
        def highlight_status(row):
            """상태 컬럼에만 배경색, 회차 컬럼에 체크무늬 적용"""
            # 모든 컬럼을 기본 스타일로 초기화
            styles = [''] * len(row)
            
            # 회차 컬럼 스타일 (홀수: 흰배경+검은글, 짝수: 검은배경+흰글)
            if '회차' in row.index:
                round_idx = row.index.get_loc('회차')
                round_val = row['회차']
                if pd.notna(round_val) and str(round_val).strip():
                    try:
                        round_num = int(float(round_val))
                        if round_num % 2 == 1:  # 홀수
                            styles[round_idx] = 'background-color: white; color: black; font-weight: bold'
                        else:  # 짝수
                            styles[round_idx] = 'background-color: #2b2b2b; color: white; font-weight: bold'
                    except:
                        pass
            
            # '상태' 컬럼의 인덱스 찾기
            if '상태' not in row.index:
                return styles
            
            status_idx = row.index.get_loc('상태')
            status_str = str(row['상태'])
            
            # 상태 컬럼에만 배경색 적용
            if '등록성공' in status_str or ('✅' in status_str and '완료' in status_str):
                # 초록 배경 (완전 성공)
                styles[status_idx] = 'background-color: #d4edda; color: #155724'
            elif '부분성공' in status_str or ('⚠️' in status_str and ('1개' in status_str or '2개' in status_str)):
                # 주황 배경 (부분 성공)
                styles[status_idx] = 'background-color: #fff3cd; color: #856404'
            elif '차량 없음' in status_str or '🚫' in status_str:
                # 노랑 배경
                styles[status_idx] = 'background-color: #ffe5b4; color: #856404'
            elif '실패' in status_str or '❌' in status_str:
                # 빨강 배경
                styles[status_idx] = 'background-color: #f8d7da; color: #721c24'
            elif '대기중' in status_str or '⏳' in status_str:
                # 회색 배경
                styles[status_idx] = 'background-color: #e2e3e5; color: #383d41'
            
            return styles
        
        # 편집 가능한 테이블로 변경 (비고만 수정 가능)
        disabled_columns = [col for col in display_df_display.columns if col != '비고']
        
        edited_df = st.data_editor(
            display_df_display,
            column_config={
                "비고": st.column_config.TextColumn(
                    "비고",
                    width="medium",
                    help="여기에 메모를 입력하세요 (자동 저장)"
                )
            },
            disabled=disabled_columns,
            hide_index=True,
            use_container_width=True,
            height=500,
            key=f"editable_table_{data_name}"
        )
        
        st.caption(f"총 {len(display_df)}개 차량 표시 중 ({date_info})")
        
        # 자동 저장: 변경사항 감지 및 자동 저장
        saved_count = 0
        changes_detected = False
        
        for idx, row in edited_df.iterrows():
            # 원본과 비교
            original_remark = display_df_display.loc[idx, '비고'] if idx in display_df_display.index else ''
            new_remark = row['비고']
            
            if original_remark != new_remark:
                changes_detected = True
                # Firebase에 자동 업데이트
                try:
                    # 날짜와 번호, 데이터소스 가져오기
                    date_val = filtered_df.loc[idx, '날짜'] if '날짜' in filtered_df.columns else selected_date
                    number = int(filtered_df.loc[idx, '번호']) if '번호' in filtered_df.columns else idx + 1
                    data_source = filtered_df.loc[idx, '데이터소스'] if '데이터소스' in filtered_df.columns else data_name
                    
                    # Firebase 업데이트
                    if update_remark(str(date_val), number, data_source, str(new_remark)):
                        saved_count += 1
                except Exception as e:
                    st.error(f"비고 자동 저장 실패: {e}")
        
        # 자동 저장 알림 및 새로고침
        if changes_detected and saved_count > 0:
            st.success(f"💾 {saved_count}개의 비고가 자동 저장되었습니다")
            st.cache_data.clear()
            time.sleep(0.5)
            st.rerun()
        
        # 안내 메시지
        st.caption("💡 비고를 입력하면 자동으로 저장됩니다")

        # CSV 다운로드 버튼 (전체 현황 기준)
        csv_data = display_df_display.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 CSV로 내보내기",
            data=csv_data,
            file_name=f"{data_name}_전체현황_{selected_date.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key=f"download_csv_{data_name}"
        )
    
    with tab2:
        st.subheader("차량번호로 조회")
        st.caption(f"{date_info} 데이터에서 검색합니다.")
        
        search_input = st.text_input("차량번호 입력 (예: 12가3456)", "", key=f"search_{data_name}")
        
        if search_input:
            # 차량번호 정규화 (공백 제거)
            search_normalized = re.sub(r'[^가-힣0-9]', '', search_input)
            
            # 검색 (필터링된 데이터에서)
            results = []
            for idx, row in filtered_df.iterrows():
                car_number = str(row.get('차량번호', ''))
                car_normalized = re.sub(r'[^가-힣0-9]', '', car_number)
                
                if search_normalized in car_normalized or car_normalized in search_normalized:
                    results.append(row)
            
            if results:
                st.success(f"✅ {len(results)}개 차량 발견")
                
                for row in results:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 3])
                        
                        # 이름 컬럼 찾기 (이름 또는 성함)
                        name = row.get('이름', row.get('성함', '-'))
                        car_num = row.get('차량번호', '-')
                        status = row.get('상태', '미등록')
                        time = row.get('처리시간', '-')
                        date = row.get('날짜', '')
                        
                        col1.write(f"**이름:** {name}")
                        col2.write(f"**차량번호:** {car_num}")
                        
                        status_text = f"{status}"
                        if date:
                            status_text += f" | {date}"
                        if time and str(time) != 'nan':
                            status_text += f" | {time}"
                        
                        if '성공' in str(status):
                            col3.success(f"✅ {status_text}")
                        elif '차량 없음' in str(status):
                            col3.info(f"🚫 {status_text}")
                        elif '실패' in str(status):
                            col3.error(f"❌ {status_text}")
                        elif '대기중' in str(status):
                            col3.info(f"⏳ {status_text}")
                        else:
                            col3.warning(f"⏳ {status_text}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ 해당 차량번호를 찾을 수 없습니다.")
    
    with tab3:
        st.subheader("📊 등록 통계")
        st.caption(f"{date_info} 데이터 기준")
        
        # === 1. 입차율 (전체 DB 대비 실제 방문율) ===
        st.markdown("---")
        st.subheader("🎯 입차율 (실제 방문율)")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 메트릭 표시
            if total > 0:
                success_rate = (success / total) * 100
                entry_rate = (success / total) * 100
                pending_rate = (pending / total) * 100
            else:
                success_rate = 0
                entry_rate = 0
                pending_rate = 0
            
            st.metric("전체 성공률", f"{success_rate:.1f}%")
            st.metric("📊 입차율", f"{entry_rate:.1f}%", 
                     help="전체 DB에 등록된 차량 중 실제로 등록에 성공한 비율")
            st.metric("⏳ 대기율", f"{pending_rate:.1f}%",
                     help="아직 처리되지 않은 차량 비율")
            
            st.caption(f"✅ 성공: {success}대 | ❌ 실패: {fail}대")
            st.caption(f"🚫 차량없음: {no_car}대 | ⏳ 대기: {pending}대")
        
        with col2:
            # 도넛 차트 (상태별 분포)
            if total > 0:
                labels = []
                values = []
                colors = []
                
                if success > 0:
                    labels.append(f'✅ 등록 성공')
                    values.append(success)
                    colors.append('#28a745')
                
                if fail > 0:
                    labels.append(f'❌ 등록 실패')
                    values.append(fail)
                    colors.append('#dc3545')
                
                if no_car > 0:
                    labels.append(f'🚫 차량 없음')
                    values.append(no_car)
                    colors.append('#ffc107')
                
                if pending > 0:
                    labels.append(f'⏳ 대기 중')
                    values.append(pending)
                    colors.append('#6c757d')
                
                fig_donut = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors),
                    textinfo='label+percent+value',
                    textfont_size=12,
                    hovertemplate='<b>%{label}</b><br>%{value}대 (%{percent})<extra></extra>'
                )])
                
                fig_donut.update_layout(
                    title=dict(
                        text="처리 현황 분포",
                        font=dict(size=16, color='white')
                    ),
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.05,
                        font=dict(color='white')
                    ),
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                
                st.plotly_chart(fig_donut, use_container_width=True, key=f"donut_{data_name}")
            else:
                st.info("표시할 데이터가 없습니다.")
        
        # === 2. 시간대별 차량 유입 분석 ===
        st.markdown("---")
        
        # 그래프 타입 선택
        col_title, col_select = st.columns([3, 1])
        with col_title:
            st.subheader("⏰ 시간대별 차량 유입 분석")
        with col_select:
            hourly_chart_type = st.selectbox(
                "그래프 유형",
                ["📊 막대 그래프", "📈 라인 차트", "🔵 영역 차트"],
                key=f"hourly_chart_type_{data_name}",
                label_visibility="collapsed"
            )
        
        if '처리시간' in filtered_df.columns:
            # 처리된 차량만 (처리시간이 있는 것)
            processed_df = filtered_df[filtered_df['처리시간'].notna() & (filtered_df['처리시간'] != '')].copy()
            
            if len(processed_df) > 0:
                # 처리시간에서 시간(hour) 추출
                def extract_hour(time_str):
                    try:
                        time_str = str(time_str).strip()
                        # "2026-01-06 18:40:15" 형식에서 시간 추출
                        if ' ' in time_str:
                            time_part = time_str.split(' ')[1]
                            hour = int(time_part.split(':')[0])
                            return hour
                        return None
                    except:
                        return None
                
                processed_df['시간대'] = processed_df['처리시간'].apply(extract_hour)
                processed_df = processed_df[processed_df['시간대'].notna()]
                
                if len(processed_df) > 0:
                    # 시간대별 집계
                    hourly_counts = processed_df.groupby('시간대').size().reset_index(name='차량수')
                    hourly_counts['시간대'] = hourly_counts['시간대'].astype(int)
                    
                    # 0~23시 전체 범위로 확장 (빈 시간대는 0으로)
                    full_hours = pd.DataFrame({'시간대': range(24)})
                    hourly_counts = full_hours.merge(hourly_counts, on='시간대', how='left').fillna(0)
                    hourly_counts['차량수'] = hourly_counts['차량수'].astype(int)
                    
                    # 시간대 레이블 생성 (0시 → "00시")
                    hourly_counts['시간'] = hourly_counts['시간대'].apply(lambda x: f"{x:02d}시")
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        fig_hourly = go.Figure()
                        
                        # 색상 그라데이션 (차량 수에 따라)
                        max_count = hourly_counts['차량수'].max()
                        colors = []
                        for count in hourly_counts['차량수']:
                            if max_count > 0:
                                intensity = count / max_count
                                colors.append(f'rgba(54, 162, 235, {0.3 + intensity * 0.7})')
                            else:
                                colors.append('rgba(54, 162, 235, 0.3)')
                        
                        # 선택된 그래프 타입에 따라 다른 차트 생성
                        if hourly_chart_type == "📊 막대 그래프":
                            fig_hourly.add_trace(go.Bar(
                                x=hourly_counts['시간'],
                                y=hourly_counts['차량수'],
                                marker=dict(
                                    color=colors,
                                    line=dict(color='rgba(54, 162, 235, 1)', width=1.5)
                                ),
                                text=hourly_counts['차량수'],
                                textposition='outside',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>차량 수: %{y}대<extra></extra>'
                            ))
                        
                        elif hourly_chart_type == "📈 라인 차트":
                            fig_hourly.add_trace(go.Scatter(
                                x=hourly_counts['시간'],
                                y=hourly_counts['차량수'],
                                mode='lines+markers+text',
                                line=dict(color='rgba(54, 162, 235, 1)', width=3),
                                marker=dict(size=8, color='rgba(54, 162, 235, 1)'),
                                text=hourly_counts['차량수'],
                                textposition='top center',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>차량 수: %{y}대<extra></extra>'
                            ))
                        
                        else:  # 영역 차트
                            fig_hourly.add_trace(go.Scatter(
                                x=hourly_counts['시간'],
                                y=hourly_counts['차량수'],
                                mode='lines',
                                fill='tozeroy',
                                line=dict(color='rgba(54, 162, 235, 1)', width=2),
                                fillcolor='rgba(54, 162, 235, 0.3)',
                                text=hourly_counts['차량수'],
                                textposition='top center',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>차량 수: %{y}대<extra></extra>'
                            ))
                        
                        fig_hourly.update_layout(
                            title=dict(
                                text="시간대별 차량 유입",
                                font=dict(size=16, color='white')
                            ),
                            xaxis=dict(
                                title=dict(text="시간대", font=dict(color='white')),
                                tickfont=dict(color='white'),
                                gridcolor='rgba(128, 128, 128, 0.2)'
                            ),
                            yaxis=dict(
                                title=dict(text="차량 수", font=dict(color='white')),
                                tickfont=dict(color='white'),
                                gridcolor='rgba(128, 128, 128, 0.2)'
                            ),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            height=400,
                            margin=dict(l=50, r=20, t=50, b=50)
                        )
                        
                        st.plotly_chart(fig_hourly, use_container_width=True, key=f"hourly_{data_name}")
                    
                    with col2:
                        # 피크 타임 정보
                        st.write("**📍 피크 타임**")
                        peak_hour = hourly_counts.loc[hourly_counts['차량수'].idxmax()]
                        st.metric("가장 바쁜 시간", 
                                 f"{int(peak_hour['시간대']):02d}시",
                                 f"{int(peak_hour['차량수'])}대")
                        
                        # Top 3 시간대
                        top3 = hourly_counts.nlargest(3, '차량수')
                        st.write("**Top 3 시간대**")
                        for idx, row in top3.iterrows():
                            if row['차량수'] > 0:
                                st.caption(f"🔸 {int(row['시간대']):02d}시: {int(row['차량수'])}대")
                    
                    st.caption(f"💡 총 {len(processed_df)}대의 차량이 처리되었습니다 ({date_info})")
                else:
                    st.info("시간대별 데이터를 추출할 수 없습니다.")
            else:
                st.info("처리된 차량이 없어 시간대별 분석을 표시할 수 없습니다.")
        else:
            st.info("처리시간 데이터가 없습니다.")
        
        # === 3. 회차별 처리 현황 ===
        st.markdown("---")
        
        # 그래프 타입 선택
        col_title2, col_select2 = st.columns([3, 1])
        with col_title2:
            st.subheader("🔄 회차별 처리 현황")
        with col_select2:
            round_chart_type = st.selectbox(
                "그래프 유형",
                ["📊 그룹 막대", "📚 스택 막대", "📈 라인 차트"],
                key=f"round_chart_type_{data_name}",
                label_visibility="collapsed"
            )
        
        if '회차' in filtered_df.columns:
            # 회차가 있는 데이터만
            round_df = filtered_df[filtered_df['회차'].notna() & (filtered_df['회차'] != '')].copy()
            
            if len(round_df) > 0:
                # 회차를 정수로 변환
                def safe_int(val):
                    try:
                        return int(float(val))
                    except:
                        return None
                
                round_df['회차_int'] = round_df['회차'].apply(safe_int)
                round_df = round_df[round_df['회차_int'].notna()]
                
                if len(round_df) > 0:
                    # 회차별 상태 집계
                    round_stats = []
                    
                    for round_num in sorted(round_df['회차_int'].unique()):
                        round_data = round_df[round_df['회차_int'] == round_num]
                        
                        total_count = len(round_data)
                        success_count = len(round_data[round_data['상태'].str.contains('성공', na=False)])
                        fail_count = len(round_data[round_data['상태'].str.contains('실패', na=False)])
                        no_car_count = len(round_data[round_data['상태'].str.contains('차량 없음', na=False)])
                        pending_count = len(round_data[round_data['상태'] == '미등록'])
                        
                        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                        
                        round_stats.append({
                            '회차': f"{int(round_num)}회차",
                            '회차_숫자': int(round_num),
                            '총 차량': total_count,
                            '성공': success_count,
                            '실패': fail_count,
                            '차량없음': no_car_count,
                            '대기': pending_count,
                            '성공률': success_rate
                        })
                    
                    round_stats_df = pd.DataFrame(round_stats)
                    
                    # 회차별 차량 수 그래프
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        fig_round = go.Figure()
                        
                        # 선택된 그래프 타입에 따라 다른 차트 생성
                        if round_chart_type in ["📊 그룹 막대", "📚 스택 막대"]:
                            # 막대 그래프 (그룹 또는 스택)
                            fig_round.add_trace(go.Bar(
                                name='✅ 성공',
                                x=round_stats_df['회차'],
                                y=round_stats_df['성공'],
                                marker=dict(color='#28a745'),
                                text=round_stats_df['성공'],
                                textposition='inside' if round_chart_type == "📚 스택 막대" else 'outside',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>성공: %{y}대<extra></extra>'
                            ))
                            
                            fig_round.add_trace(go.Bar(
                                name='❌ 실패',
                                x=round_stats_df['회차'],
                                y=round_stats_df['실패'],
                                marker=dict(color='#dc3545'),
                                text=round_stats_df['실패'],
                                textposition='inside' if round_chart_type == "📚 스택 막대" else 'outside',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>실패: %{y}대<extra></extra>'
                            ))
                            
                            fig_round.add_trace(go.Bar(
                                name='🚫 차량없음',
                                x=round_stats_df['회차'],
                                y=round_stats_df['차량없음'],
                                marker=dict(color='#ffc107'),
                                text=round_stats_df['차량없음'],
                                textposition='inside' if round_chart_type == "📚 스택 막대" else 'outside',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>차량없음: %{y}대<extra></extra>'
                            ))
                            
                            fig_round.add_trace(go.Bar(
                                name='⏳ 대기',
                                x=round_stats_df['회차'],
                                y=round_stats_df['대기'],
                                marker=dict(color='#6c757d'),
                                text=round_stats_df['대기'],
                                textposition='inside' if round_chart_type == "📚 스택 막대" else 'outside',
                                textfont=dict(size=10, color='white'),
                                hovertemplate='<b>%{x}</b><br>대기: %{y}대<extra></extra>'
                            ))
                        
                        else:  # 라인 차트
                            fig_round.add_trace(go.Scatter(
                                name='✅ 성공',
                                x=round_stats_df['회차'],
                                y=round_stats_df['성공'],
                                mode='lines+markers',
                                line=dict(color='#28a745', width=3),
                                marker=dict(size=8, color='#28a745'),
                                hovertemplate='<b>%{x}</b><br>성공: %{y}대<extra></extra>'
                            ))
                            
                            fig_round.add_trace(go.Scatter(
                                name='❌ 실패',
                                x=round_stats_df['회차'],
                                y=round_stats_df['실패'],
                                mode='lines+markers',
                                line=dict(color='#dc3545', width=3),
                                marker=dict(size=8, color='#dc3545'),
                                hovertemplate='<b>%{x}</b><br>실패: %{y}대<extra></extra>'
                            ))
                            
                            fig_round.add_trace(go.Scatter(
                                name='🚫 차량없음',
                                x=round_stats_df['회차'],
                                y=round_stats_df['차량없음'],
                                mode='lines+markers',
                                line=dict(color='#ffc107', width=3),
                                marker=dict(size=8, color='#ffc107'),
                                hovertemplate='<b>%{x}</b><br>차량없음: %{y}대<extra></extra>'
                            ))
                            
                            fig_round.add_trace(go.Scatter(
                                name='⏳ 대기',
                                x=round_stats_df['회차'],
                                y=round_stats_df['대기'],
                                mode='lines+markers',
                                line=dict(color='#6c757d', width=3),
                                marker=dict(size=8, color='#6c757d'),
                                hovertemplate='<b>%{x}</b><br>대기: %{y}대<extra></extra>'
                            ))
                        
                        fig_round.update_layout(
                            title=dict(
                                text="회차별 처리 차량 수",
                                font=dict(size=16, color='white')
                            ),
                            xaxis=dict(
                                title=dict(text="회차", font=dict(color='white')),
                                tickfont=dict(color='white'),
                                gridcolor='rgba(128, 128, 128, 0.2)'
                            ),
                            yaxis=dict(
                                title=dict(text="차량 수", font=dict(color='white')),
                                tickfont=dict(color='white'),
                                gridcolor='rgba(128, 128, 128, 0.2)'
                            ),
                            barmode='stack' if round_chart_type == "📚 스택 막대" else 'group',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1,
                                font=dict(color='white')
                            ),
                            height=400,
                            margin=dict(l=50, r=20, t=80, b=50)
                        )
                        
                        st.plotly_chart(fig_round, use_container_width=True, key=f"round_{data_name}")
                    
                    with col2:
                        st.write("**회차별 요약**")
                        # 가장 바쁜 회차
                        busiest = round_stats_df.loc[round_stats_df['총 차량'].idxmax()]
                        st.metric("가장 바쁜 회차", 
                                 busiest['회차'], 
                                 f"{busiest['총 차량']}대")
                        
                        # 가장 성공률 높은 회차
                        best_success = round_stats_df.loc[round_stats_df['성공'].idxmax()]
                        st.metric("최다 성공 회차", 
                                 best_success['회차'], 
                                 f"{best_success['성공률']:.1f}%")
                        
                        # 평균 성공률
                        avg_success_rate = round_stats_df['성공률'].mean()
                        st.metric("평균 성공률", f"{avg_success_rate:.1f}%")
                    
                    # 상세 테이블
                    st.write("**회차별 상세 현황**")
                    display_round_df = round_stats_df[['회차', '총 차량', '성공', '실패', '차량없음', '대기']].copy()
                    display_round_df['성공률'] = round_stats_df['성공률'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(display_round_df, use_container_width=True, hide_index=True)
                    
                    st.caption(f"💡 총 {len(round_df['회차_int'].unique())}개 회차가 실행되었습니다 ({date_info})")
                else:
                    st.info("회차 데이터를 처리할 수 없습니다.")
            else:
                st.info("회차 정보가 있는 데이터가 없습니다.")
        else:
            st.info("회차 데이터가 없습니다.")
        
        # === 4. 상태별 통계 (기존) ===
        st.markdown("---")
        
        # 그래프 타입 선택
        col_title3, col_select3 = st.columns([3, 1])
        with col_title3:
            st.subheader("📈 상태별 분포")
        with col_select3:
            status_chart_type = st.selectbox(
                "그래프 유형",
                ["📊 막대 그래프", "🍩 도넛 차트", "🥧 파이 차트"],
                key=f"status_chart_type_{data_name}",
                label_visibility="collapsed"
            )
        
        if '상태' in filtered_df.columns:
            status_counts = filtered_df['상태'].value_counts()
            
            if len(status_counts) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    # 데이터 준비
                    status_labels = []
                    status_values = []
                    status_colors = []
                    
                    for status, count in status_counts.items():
                        # 상태별 이모지와 색상
                        if '성공' in str(status):
                            emoji = "✅"
                            color = '#28a745'
                        elif '차량 없음' in str(status) or '차량없음' in str(status):
                            emoji = "🚫"
                            color = '#ffc107'
                        elif '실패' in str(status):
                            emoji = "❌"
                            color = '#dc3545'
                        else:
                            emoji = "⏳"
                            color = '#6c757d'
                        
                        status_labels.append(f"{emoji} {status}")
                        status_values.append(count)
                        status_colors.append(color)
                    
                    # 선택된 그래프 타입에 따라 다른 차트 생성
                    fig_status = go.Figure()
                    
                    if status_chart_type == "📊 막대 그래프":
                        fig_status.add_trace(go.Bar(
                            x=status_labels,
                            y=status_values,
                            marker=dict(color=status_colors),
                            text=status_values,
                            textposition='outside',
                            textfont=dict(size=12, color='white'),
                            hovertemplate='<b>%{x}</b><br>차량 수: %{y}대<extra></extra>'
                        ))
                        
                        fig_status.update_layout(
                            title=dict(
                                text="전체 상태 분포",
                                font=dict(size=16, color='white')
                            ),
                            xaxis=dict(
                                title=dict(text="상태", font=dict(color='white')),
                                tickfont=dict(color='white'),
                                gridcolor='rgba(128, 128, 128, 0.2)'
                            ),
                            yaxis=dict(
                                title=dict(text="차량 수", font=dict(color='white')),
                                tickfont=dict(color='white'),
                                gridcolor='rgba(128, 128, 128, 0.2)'
                            ),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            height=350,
                            margin=dict(l=50, r=20, t=50, b=100)
                        )
                    
                    elif status_chart_type == "🍩 도넛 차트":
                        fig_status.add_trace(go.Pie(
                            labels=status_labels,
                            values=status_values,
                            hole=0.4,
                            marker=dict(colors=status_colors),
                            textinfo='label+percent',
                            textfont=dict(size=12, color='white'),
                            hovertemplate='<b>%{label}</b><br>%{value}대 (%{percent})<extra></extra>'
                        ))
                        
                        fig_status.update_layout(
                            title=dict(
                                text="전체 상태 분포",
                                font=dict(size=16, color='white')
                            ),
                            showlegend=False,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            height=350,
                            margin=dict(l=20, r=20, t=50, b=20)
                        )
                    
                    else:  # 파이 차트
                        fig_status.add_trace(go.Pie(
                            labels=status_labels,
                            values=status_values,
                            marker=dict(colors=status_colors),
                            textinfo='label+percent',
                            textfont=dict(size=12, color='white'),
                            hovertemplate='<b>%{label}</b><br>%{value}대 (%{percent})<extra></extra>'
                        ))
                        
                        fig_status.update_layout(
                            title=dict(
                                text="전체 상태 분포",
                                font=dict(size=16, color='white')
                            ),
                            showlegend=False,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            height=350,
                            margin=dict(l=20, r=20, t=50, b=20)
                        )
                    
                    st.plotly_chart(fig_status, use_container_width=True, key=f"status_chart_{data_name}")
                
                with col2:
                    st.write("**상태별 비율**")
                    
                    # 메트릭으로 표시
                    status_pct = (status_counts / status_counts.sum() * 100).round(1)
                    
                    for status, pct in status_pct.items():
                        # 상태별 이모지
                        if '성공' in str(status):
                            emoji = "✅"
                        elif '차량 없음' in str(status) or '차량없음' in str(status):
                            emoji = "🚫"
                        elif '실패' in str(status):
                            emoji = "❌"
                        else:
                            emoji = "⏳"
                        
                        # 개수와 비율 표시
                        count = status_counts[status]
                        st.metric(f"{emoji} {status}", f"{count}대", f"{pct}%")
                    
                    st.caption(f"총 {status_counts.sum()}대")
            else:
                st.info("표시할 데이터가 없습니다.")
        
        # === 5. 최근 처리 내역 (기존) ===
        st.markdown("---")
        st.subheader("🕐 최근 처리 내역")
        
        if '처리시간' in filtered_df.columns:
            recent_df = filtered_df[filtered_df['처리시간'].notna()].sort_values('처리시간', ascending=False).head(10)
            if len(recent_df) > 0:
                # 컬럼명 동적으로 찾기
                display_cols = []
                
                # 날짜 컬럼
                if '날짜' in recent_df.columns:
                    display_cols.append('날짜')
                
                # 이름 컬럼 (이름 또는 성함)
                name_col = None
                for col in ['이름', '성함']:
                    if col in recent_df.columns:
                        name_col = col
                        display_cols.append(col)
                        break
                
                # 차량번호 컬럼
                if '차량번호' in recent_df.columns:
                    display_cols.append('차량번호')
                
                # 상태 컬럼
                if '상태' in recent_df.columns:
                    display_cols.append('상태')
                
                # 처리시간 컬럼
                if '처리시간' in recent_df.columns:
                    display_cols.append('처리시간')
                
                # 존재하는 컬럼만 표시
                existing_cols = [col for col in display_cols if col in recent_df.columns]
                if existing_cols:
                    st.dataframe(recent_df[existing_cols], use_container_width=True, hide_index=True)
                else:
                    st.dataframe(recent_df, use_container_width=True, hide_index=True)
            else:
                st.info("처리된 내역이 없습니다.")
        else:
            st.info("처리시간 데이터가 없습니다.")

    # 각 탭 렌더링 후 공통 사이드바 출력
    render_sidebar(data_name, date_info, df, csv_path, is_all_mode=is_all_mode)

# 각 탭별로 데이터 로드 및 렌더링
with tab_db:
    csv_path = DB_CSV_PATH
    data_name = "주차 명단"
    
    # Firebase에서 주차 명단 데이터만 필터링
    if FIREBASE_AVAILABLE:
        df_all = load_data_from_firebase()
        if df_all is not None and '데이터소스' in df_all.columns:
            # 데이터소스가 "주차 명단"인 것만
            df = df_all[df_all['데이터소스'] == '주차 명단'].copy()
        else:
            df = df_all if df_all is not None else None
        
        if df is None or len(df) == 0:  # Firebase 실패 시 로컬 CSV
            file_mtime = get_file_mtime(csv_path)
            df = load_data(csv_path, file_mtime)
    else:
        # Firebase 사용 불가 시 로컬 CSV
        file_mtime = get_file_mtime(csv_path)
        df = load_data(csv_path, file_mtime)
    
    render_data_tab(df, data_name, csv_path, is_all_mode=False)

with tab_manual:
    data_name = "수동 입력"
    
    # Firebase에서 수동 입력 데이터만 필터링
    if FIREBASE_AVAILABLE:
        df_all = load_data_from_firebase()
        if df_all is not None and '데이터소스' in df_all.columns:
            # 데이터소스가 "일일 등록"인 것만 (수동 입력)
            df = df_all[df_all['데이터소스'] == '일일 등록'].copy()
        else:
            df = df_all if df_all is not None else None
    else:
        # 로컬 모드에서는 빈 데이터
        df = None
    
    render_data_tab(df, data_name, '', is_all_mode=False)

with tab_all:
    data_name = "전체 (주차명단 + 수동입력)"
    
    # Firebase 우선
    if FIREBASE_AVAILABLE:
        df_all = load_data_from_firebase()
        if df_all is None:  # Firebase 실패 시 로컬 CSV
            # 두 파일 모두 읽기
            db_mtime = get_file_mtime(DB_CSV_PATH)
            daily_mtime = get_file_mtime(DAILY_CSV_PATH)
            df_db = load_data(DB_CSV_PATH, db_mtime)
            df_daily = load_data(DAILY_CSV_PATH, daily_mtime)
            
            # 데이터 합치기
            if df_db is not None and df_daily is not None:
                # 컬럼 통일 (이름/성함 통일)
                if '성함' in df_db.columns:
                    df_db = df_db.rename(columns={'성함': '이름'})
                if '이름' not in df_db.columns and '성함' not in df_db.columns:
                    df_db['이름'] = ''
                if '이름' not in df_daily.columns:
                    df_daily['이름'] = ''
                
                # 데이터 소스 구분을 위한 컬럼 추가
                df_db['데이터_소스'] = '주차 명단'
                df_daily['데이터_소스'] = '수동 입력'
                
                # 합치기
                df_all = pd.concat([df_db, df_daily], ignore_index=True)
                csv_path = f"{DB_CSV_PATH}, {DAILY_CSV_PATH}"  # 두 파일 경로 표시용
            elif df_db is not None:
                df_all = df_db
                df_all['데이터_소스'] = '주차 명단'
                csv_path = DB_CSV_PATH
            elif df_daily is not None:
                df_all = df_daily
                df_all['데이터_소스'] = '수동 입력'
                csv_path = DAILY_CSV_PATH
            else:
                df_all = None
                csv_path = ''
    else:
        # Firebase 없을 때 로컬 CSV 로드
        db_mtime = get_file_mtime(DB_CSV_PATH)
        daily_mtime = get_file_mtime(DAILY_CSV_PATH)
        df_db = load_data(DB_CSV_PATH, db_mtime)
        df_daily = load_data(DAILY_CSV_PATH, daily_mtime)
        
        # 데이터 합치기
        if df_db is not None and df_daily is not None:
            # 컬럼 통일
            if '성함' in df_db.columns:
                df_db = df_db.rename(columns={'성함': '이름'})
            if '이름' not in df_db.columns and '성함' not in df_db.columns:
                df_db['이름'] = ''
            if '이름' not in df_daily.columns:
                df_daily['이름'] = ''
            
            df_db['데이터_소스'] = '주차 명단'
            df_daily['데이터_소스'] = '수동 입력'
            
            df_all = pd.concat([df_db, df_daily], ignore_index=True)
            csv_path = f"{DB_CSV_PATH}, {DAILY_CSV_PATH}"
        elif df_db is not None:
            df_all = df_db
            df_all['데이터_소스'] = '주차 명단'
            csv_path = DB_CSV_PATH
        elif df_daily is not None:
            df_all = df_daily
            df_all['데이터_소스'] = '수동 입력'
            csv_path = DAILY_CSV_PATH
        else:
            df_all = None
            csv_path = ''
    
    render_data_tab(df_all, data_name, csv_path if 'csv_path' in locals() else '', is_all_mode=True)
