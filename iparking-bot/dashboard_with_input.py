# 대시보드에 입력 폼 + 실시간 로그 표시
import streamlit as st
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="차량 등록 시스템", page_icon="🚗", layout="wide")

# 로그 디렉토리
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

st.title("🚗 차량 등록 시스템")

# 사이드바에 입력 폼
with st.sidebar:
    st.header("📝 차량 등록")
    
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("성함", placeholder="홍길동")
        car_number = st.text_input("차량번호", placeholder="12가3456")
        
        submitted = st.form_submit_button("🚀 등록 시작", use_container_width=True)
        
        if submitted and name and car_number:
            # 세션 스테이트에 저장
            if 'processing' not in st.session_state:
                st.session_state.processing = []
            
            # 봇 실행 (백그라운드)
            process = subprocess.Popen(
                ['python', 'bot_with_logging.py', name, car_number],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.session_state.processing.append({
                'name': name,
                'car_number': car_number,
                'log_file': LOG_DIR / f"{car_number}_{timestamp}.log",
                'process': process,
                'timestamp': timestamp
            })
            
            st.success(f"✅ {car_number} 등록 시작!")
            st.rerun()

# 메인 영역: 처리 중인 차량 목록
st.header("📋 처리 현황")

if 'processing' not in st.session_state or len(st.session_state.processing) == 0:
    st.info("등록 대기 중... 왼쪽에서 차량을 등록하세요.")
else:
    # 탭으로 각 차량 표시
    tabs = st.tabs([f"🚗 {item['car_number']}" for item in st.session_state.processing])
    
    for idx, (tab, item) in enumerate(zip(tabs, st.session_state.processing)):
        with tab:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(f"{item['name']} - {item['car_number']}")
                st.caption(f"시작 시간: {item['timestamp']}")
            
            with col2:
                if st.button("🔄 새로고침", key=f"refresh_{idx}"):
                    st.rerun()
            
            # 로그 파일 읽기
            log_container = st.empty()
            
            if item['log_file'].exists():
                with open(item['log_file'], 'r', encoding='utf-8') as f:
                    logs = f.read()
                    
                log_container.text_area(
                    "실시간 처리 로그",
                    logs,
                    height=400,
                    key=f"log_{idx}"
                )
                
                # 프로세스 완료 확인
                if item['process'].poll() is not None:
                    if "✅ 모든 처리 완료!" in logs:
                        st.success("✅ 등록 완료!")
                    else:
                        st.error("❌ 등록 실패")
            else:
                st.info("⏳ 로그 생성 대기 중...")
                # 자동 새로고침 (3초 후)
                time.sleep(1)
                st.rerun()

# 자동 새로고침 (처리 중인 항목이 있을 때만)
if 'processing' in st.session_state and len(st.session_state.processing) > 0:
    # 처리 중인지 확인
    any_running = any(item['process'].poll() is None for item in st.session_state.processing)
    
    if any_running:
        st.caption("⚡ 3초마다 자동 새로고침 중...")
        time.sleep(3)
        st.rerun()

# 하단: 최근 로그 파일 목록
st.markdown("---")
st.subheader("📂 최근 처리 기록")

log_files = sorted(LOG_DIR.glob("*.log"), key=os.path.getmtime, reverse=True)[:5]

if log_files:
    for log_file in log_files:
        with st.expander(f"📄 {log_file.name}"):
            with open(log_file, 'r', encoding='utf-8') as f:
                st.code(f.read(), language='text')
else:
    st.info("처리 기록이 없습니다.")
