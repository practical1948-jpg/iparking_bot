# 가장 간단한 대시보드 입력 + 실시간 로그
import streamlit as st
import time
from datetime import datetime
from firebase_helper import save_parking_record, get_parking_records, append_log, get_kst_now

st.set_page_config(page_title="차량 등록", page_icon="🚗", layout="wide")

st.title("🚗 차량 등록 시스템")

# 사이드바: 입력 폼
with st.sidebar:
    st.header("📝 빠른 등록")
    
    with st.form("quick_register", clear_on_submit=True):
        car_name = st.text_input("성함", placeholder="홍길동")
        car_number = st.text_input("차량번호", placeholder="12가3456")
        
        submitted = st.form_submit_button("✅ 등록", use_container_width=True)
        
        if submitted:
            if not car_name or not car_number:
                st.error("성함과 차량번호를 입력하세요")
            else:
                # 차량번호 정규화
                normalized = car_number.replace(" ", "").replace("-", "")
                
                # Firebase에 저장
                today = get_kst_now().strftime('%Y-%m-%d')
                now = get_kst_now().strftime('%Y-%m-%d %H:%M:%S')
                
                data = {
                    '회차': 0,
                    '번호': int(datetime.now().timestamp()) % 1000,  # 간단한 번호
                    '성함': car_name,
                    '차량번호': normalized,
                    '상태': '미등록',
                    '처리시간': '',
                    '데이터소스': '일일 등록',
                    '비고': f'대시보드 입력 ({now})',
                    '처리로그': f'[{get_kst_now().strftime("%H:%M:%S")}] 등록 대기 중...'
                }
                
                if save_parking_record(data):
                    st.success(f"✅ {car_number} 등록 완료!")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ 등록 실패")
    
    st.markdown("---")
    st.caption("💡 등록하면 아래 목록에 나타납니다")
    st.caption("🔄 봇이 자동으로 처리합니다")

# 메인: 오늘 등록 현황
st.header("📋 오늘 등록 현황")

# 데이터 로드
today = get_kst_now().strftime('%Y-%m-%d')
records = get_parking_records(today)

if not records:
    st.info("오늘 등록된 차량이 없습니다. 왼쪽에서 등록하세요.")
else:
    # 필터: 일일 등록만
    daily_records = [r for r in records if r.get('데이터소스') == '일일 등록']
    
    if not daily_records:
        st.info("일일 등록 차량이 없습니다.")
    else:
        st.caption(f"총 {len(daily_records)}대 등록")
        
        # 탭으로 구분
        tabs = st.tabs(["📊 전체 현황", "🔍 상세 로그"])
        
        with tabs[0]:
            # 간단한 테이블
            import pandas as pd
            df = pd.DataFrame(daily_records)
            
            # 표시 컬럼
            display_cols = ['성함', '차량번호', '상태', '처리시간', '비고']
            existing_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[existing_cols],
                use_container_width=True,
                hide_index=True,
                height=400
            )
        
        with tabs[1]:
            # 각 차량별 로그 표시
            for record in daily_records:
                with st.expander(f"🚗 {record['차량번호']} ({record['성함']}) - {record['상태']}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**상태:** {record.get('상태', '-')}")
                        st.write(f"**처리시간:** {record.get('처리시간', '-')}")
                        st.write(f"**비고:** {record.get('비고', '-')}")
                    
                    with col2:
                        if st.button("🔄 새로고침", key=f"refresh_{record['번호']}"):
                            st.rerun()
                    
                    # 로그 표시
                    if '처리로그' in record and record['처리로그']:
                        st.text_area(
                            "처리 로그",
                            record['처리로그'],
                            height=200,
                            key=f"log_{record['번호']}"
                        )
                    else:
                        st.info("처리 로그가 없습니다")

# 자동 새로고침 (미등록 항목이 있을 때)
if daily_records and any(r.get('상태') == '미등록' for r in daily_records):
    st.caption("⚡ 5초마다 자동 새로고침 중...")
    time.sleep(5)
    st.rerun()
