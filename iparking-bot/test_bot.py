# 실시간 로그 테스트용 간단한 봇
from logger_helper import enable_dual_logging
import time
from datetime import datetime

def main():
    # 로깅 시작 (이제 모든 print가 파일에도 저장됨)
    enable_dual_logging()
    
    print("=" * 60)
    print("🚗 차량 등록 테스트 봇 시작")
    print("=" * 60)
    
    # 차량 정보 입력
    name = input("\n성함: ")
    car_number = input("차량번호: ")
    
    print("\n" + "=" * 60)
    print(f"📝 등록 시작: {name} ({car_number})")
    print("=" * 60)
    
    # 1단계: 입차 확인
    print("\n[1/3] 🔍 입차 여부 확인 중...")
    for i in range(3):
        time.sleep(1)
        print(f"  진행률: {(i+1)*33}%")
    print("✅ 입차 확인 완료!")
    
    # 2단계: 주차권 등록
    print("\n[2/3] 🎫 주차권 등록 중...")
    for tab in range(3):
        print(f"\n  탭 {tab+1}/3 처리 중...")
        time.sleep(1)
        print(f"  ✅ 탭 {tab+1} 등록 성공")
    print("\n✅ 주차권 등록 완료!")
    
    # 3단계: 완료
    print("\n[3/3] 📊 최종 처리 중...")
    time.sleep(1)
    
    print("\n" + "=" * 60)
    print("✅ 모든 처리 완료!")
    print(f"📅 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
