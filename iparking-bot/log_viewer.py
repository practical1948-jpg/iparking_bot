# 터미널 봇의 로그를 실시간으로 보는 대시보드 페이지
import streamlit as st
import os
from datetime import datetime
from pathlib import Path
import time

st.set_page_config(page_title="실시간 로그 뷰어", page_icon="📋", layout="wide")

st.title("📋 봇 실시간 로그")

# 로그 디렉토리
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 사이드바: 로그 파일 선택
st.sidebar.header("📂 로그 파일")

log_files = sorted(LOG_DIR.glob("*.log"), key=os.path.getmtime, reverse=True)

if not log_files:
    st.warning("⚠️ 로그 파일이 없습니다. 봇을 실행하세요.")
    st.stop()

# 가장 최근 파일 기본 선택
selected_file = st.sidebar.selectbox(
    "로그 파일 선택",
    log_files,
    format_func=lambda x: f"{x.name} ({datetime.fromtimestamp(os.path.getmtime(x)).strftime('%H:%M:%S')})"
)

st.sidebar.markdown("---")

# 자동 새로고침 설정
auto_refresh = st.sidebar.checkbox("🔄 자동 새로고침 (5초)", value=True)

if auto_refresh:
    st.sidebar.caption("⏱️ 5초마다 자동 갱신 중...")

# 수동 새로고침 버튼
if st.sidebar.button("🔄 지금 새로고침", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 메인: 로그 내용 표시
st.subheader(f"📄 {selected_file.name}")

col1, col2 = st.columns([3, 1])

with col1:
    file_time = datetime.fromtimestamp(os.path.getmtime(selected_file))
    st.caption(f"수정 시간: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
    file_size = os.path.getsize(selected_file)
    st.caption(f"크기: {file_size:,} bytes")

# 로그 내용 읽기
try:
    with open(selected_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # 마지막 N줄만 표시 (옵션)
    show_lines = st.sidebar.slider("표시할 줄 수", 50, 1000, 500, 50)
    
    lines = log_content.split('\n')
    if len(lines) > show_lines:
        display_content = '\n'.join(lines[-show_lines:])
        st.info(f"ℹ️ 마지막 {show_lines}줄만 표시 중 (전체: {len(lines)}줄)")
    else:
        display_content = log_content
        st.info(f"📊 전체 {len(lines)}줄 표시 중")
    
    # 로그 표시 (스크롤 가능한 텍스트 영역)
    st.text_area(
        "로그 내용",
        display_content,
        height=600,
        key="log_content",
        label_visibility="collapsed"
    )
    
    # 다운로드 버튼
    st.download_button(
        label="📥 로그 다운로드",
        data=log_content,
        file_name=selected_file.name,
        mime="text/plain"
    )
    
except Exception as e:
    st.error(f"❌ 로그 읽기 실패: {e}")

# 자동 새로고침
if auto_refresh:
    time.sleep(5)
    st.rerun()
