# iParking 주차권 등록 실시간 대시보드
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import re
import time
import glob
import shutil
import json
import hashlib

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

# 자동 새로고침 설정 (5초마다)
if AUTO_REFRESH_AVAILABLE:
    # 5000ms = 5초마다 자동 새로고침
    st_autorefresh(interval=5000, key="datarefresh")

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

# CSV 파일 경로 (기본값)
BASE_PATH = r"C:\Users\myc43\OneDrive - ETERNAL LIBRTY POLICY INSTITUTE\바탕 화면\업무 자료\dev\iparking-bot"
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
st.sidebar.markdown(f"일일 등록: {'✅ 존재' if daily_exists else '❌ 없음'}")
st.sidebar.markdown("---")

# 파일 수정 시간 가져오기 함수
def get_file_mtime(csv_path):
    """파일의 수정 시간을 반환 (캐시 키로 사용)"""
    if os.path.exists(csv_path):
        return os.path.getmtime(csv_path)
    return None

# 데이터 로드 함수 (파일 수정 시간을 캐시 키에 포함)
@st.cache_data(ttl=3)  # 3초마다 캐시 체크
def load_data(csv_path, file_mtime):
    """
    파일 수정 시간(file_mtime)이 변경되면 자동으로 새로운 데이터를 로드
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
        # 통합 모드: 주차명단 + 일일등록
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
tab_db, tab_daily, tab_all = st.tabs(["📊 주차 명단", "📝 일일 등록", "🔗 전체"])

# 각 탭별 데이터 처리 함수
def render_data_tab(df, data_name, csv_path, is_all_mode=False):
    """각 탭의 데이터를 렌더링하는 함수"""
    if df is None or len(df) == 0:
        st.warning(f"❌ {data_name} 데이터를 불러올 수 없습니다.")
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
        # 전체: 선택한 날짜 처리된 모든 데이터 (주차명단 + 일일등록)
        filtered_df = df[df['날짜'] == selected_date].copy()
        date_info = f"{selected_date.strftime('%Y년 %m월 %d일')} (전체)"
    else:
        # 일일 등록: 선택한 날짜 처리된 것만
        filtered_df = df[df['날짜'] == selected_date].copy()
        date_info = f"{selected_date.strftime('%Y년 %m월 %d일')}"
    
    # 상단 통계 (필터링된 데이터 기준) - 통일된 형식
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(filtered_df)
    success = len(filtered_df[filtered_df['상태'].str.contains('성공', na=False)]) if '상태' in filtered_df.columns else 0
    fail = len(filtered_df[filtered_df['상태'].str.contains('실패', na=False)]) if '상태' in filtered_df.columns else 0
    pending = len(filtered_df[filtered_df['상태'] == '미등록']) if '상태' in filtered_df.columns else total
    
    # 통일된 형식으로 표시 (delta 제거)
    col1.metric("📊 총 차량", f"{total}대")
    col2.metric("✅ 등록 성공", f"{success}대")
    col3.metric("❌ 등록 실패", f"{fail}대")
    col4.metric("⏳ 대기 중", f"{pending}대")
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📋 전체 현황", "🔍 차량 조회", "📊 통계"])
    
    with tab1:
        st.subheader("전체 등록 현황")
        
        # 상태 필터
        status_filter_option = st.selectbox(
            "상태 필터",
            ["전체", "등록 성공", "등록 실패", "차량 없음", "미등록"],
            key=f"status_filter_{data_name}"
        )
        
        # 상태 필터 적용
        display_df = filtered_df.copy()
        if status_filter_option == "등록 성공":
            display_df = display_df[display_df['상태'].str.contains('성공', na=False)]
        elif status_filter_option == "등록 실패":
            display_df = display_df[display_df['상태'].str.contains('실패', na=False)]
        elif status_filter_option == "차량 없음":
            display_df = display_df[display_df['상태'].str.contains('차량 없음', na=False)]
        elif status_filter_option == "미등록":
            display_df = display_df[display_df['상태'] == '미등록']
        
        # 날짜 컬럼 제거 (표시용)
        display_df_display = display_df.drop(columns=['날짜'], errors='ignore').copy()
        
        # 회차 컬럼 순서 조정 (맨 앞으로)
        if '회차' in display_df_display.columns:
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
                if '성공' in status_str:
                    return f"✅ {status_str}"
                elif '차량 없음' in status_str:
                    return f"🚫 {status_str}"
                elif '실패' in status_str:
                    return f"❌ {status_str}"
                elif status_str == '미등록':
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
            if '성공' in status_str or '✅' in status_str:
                # 초록 배경
                styles[status_idx] = 'background-color: #d4edda; color: #155724'
            elif '차량 없음' in status_str or '🚫' in status_str:
                # 노랑 배경
                styles[status_idx] = 'background-color: #fff3cd; color: #856404'
            elif '실패' in status_str or '❌' in status_str:
                # 빨강 배경
                styles[status_idx] = 'background-color: #f8d7da; color: #721c24'
            elif '미등록' in status_str or '⏳' in status_str:
                # 투명 (배경색 없음)
                styles[status_idx] = ''
            
            return styles
        
        if '상태' in display_df_display.columns:
            styled_df = display_df_display.style.apply(highlight_status, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=500)
        else:
            st.dataframe(display_df_display, use_container_width=True, height=500)
        
        st.caption(f"총 {len(display_df)}개 차량 표시 중 ({date_info})")

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
                        else:
                            col3.warning(f"⏳ {status_text}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ 해당 차량번호를 찾을 수 없습니다.")
    
    with tab3:
        st.subheader("등록 통계")
        st.caption(f"{date_info} 데이터 기준")
        
        # 상태별 통계
        if '상태' in filtered_df.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**상태별 분포**")
                status_counts = filtered_df['상태'].value_counts()
                if len(status_counts) > 0:
                    st.bar_chart(status_counts)
                else:
                    st.info("표시할 데이터가 없습니다.")
            
            with col2:
                st.write("**성공률**")
                if total > 0:
                    success_rate = (success / total) * 100
                    st.metric("전체 성공률", f"{success_rate:.1f}%")
                    
                    # 프로그레스 바
                    st.progress(success_rate / 100)
                    
                    st.write(f"- 성공: {success}대")
                    st.write(f"- 실패: {fail}대")
                    st.write(f"- 대기: {pending}대")
                else:
                    st.info("표시할 데이터가 없습니다.")
        
        # 최근 처리 내역
        st.write("**최근 처리 내역 (최신 10개)**")
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
                    st.dataframe(recent_df[existing_cols], use_container_width=True)
                else:
                    st.dataframe(recent_df, use_container_width=True)
            else:
                st.info("처리된 내역이 없습니다.")

    # 각 탭 렌더링 후 공통 사이드바 출력
    render_sidebar(data_name, date_info, df, csv_path, is_all_mode=is_all_mode)

# 각 탭별로 데이터 로드 및 렌더링
with tab_db:
    csv_path = DB_CSV_PATH
    data_name = "주차 명단"
    file_mtime = get_file_mtime(csv_path)
    df = load_data(csv_path, file_mtime)
    render_data_tab(df, data_name, csv_path, is_all_mode=False)

with tab_daily:
    csv_path = DAILY_CSV_PATH
    data_name = "일일 등록"
    file_mtime = get_file_mtime(csv_path)
    df = load_data(csv_path, file_mtime)
    render_data_tab(df, data_name, csv_path, is_all_mode=False)

with tab_all:
    data_name = "전체 (주차명단 + 일일등록)"
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
        df_daily['데이터_소스'] = '일일 등록'
        
        # 합치기
        df = pd.concat([df_db, df_daily], ignore_index=True)
        csv_path = f"{DB_CSV_PATH}, {DAILY_CSV_PATH}"  # 두 파일 경로 표시용
    elif df_db is not None:
        df = df_db
        df['데이터_소스'] = '주차 명단'
        csv_path = DB_CSV_PATH
    elif df_daily is not None:
        df = df_daily
        df['데이터_소스'] = '일일 등록'
        csv_path = DAILY_CSV_PATH
    else:
        df = None
    
    render_data_tab(df, data_name, csv_path, is_all_mode=True)
