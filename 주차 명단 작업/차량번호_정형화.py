"""
차량번호 정형화 스크립트
CSV 파일의 차량번호에서 공백을 제거하고 정형화합니다.
"""

import csv
import sys
from pathlib import Path


def normalize_car_number(car_number: str) -> str:
    """
    차량번호를 정형화합니다.
    - 모든 공백 제거
    - 앞뒤 공백 제거
    """
    if not car_number:
        return ''
    
    # 모든 공백 제거 (스페이스, 탭 등)
    normalized = ''.join(car_number.split())
    
    return normalized


def process_csv_file(input_file: str, output_file: str = None, backup: bool = False, verbose: bool = False):
    """
    CSV 파일의 차량번호를 정형화합니다.
    
    Args:
        input_file: 입력 CSV 파일 경로
        output_file: 출력 CSV 파일 경로 (None이면 원본 파일 수정)
        backup: 백업 파일 생성 여부 (기본값: False)
        verbose: 상세 출력 여부
    """
    if not Path(input_file).exists():
        print(f"오류: 파일을 찾을 수 없습니다: {input_file}")
        return False
    
    # 백업 파일 생성 (옵션)
    if backup:
        import shutil
        backup_file = str(Path(input_file).with_suffix('.backup.csv'))
        shutil.copy2(input_file, backup_file)
        if verbose:
            print(f"백업 파일 생성: {backup_file}")
    
    data = []
    changes_count = 0
    changed_items = []
    
    # CSV 파일 읽기
    if verbose:
        print(f"\nCSV 파일 읽는 중: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            original_car = str(row.get('차량번호', '')).strip()
            normalized_car = normalize_car_number(original_car)
            
            if original_car != normalized_car:
                changes_count += 1
                if verbose:
                    changed_items.append((original_car, normalized_car))
            
            row['차량번호'] = normalized_car
            data.append(row)
    
    # 변경 사항 출력
    if verbose and changed_items:
        print("\n변경된 차량번호:")
        for original, normalized in changed_items:
            print(f"  '{original}' -> '{normalized}'")
    
    # 정형화된 데이터 저장
    save_file = output_file if output_file else input_file
    if verbose:
        print(f"\n정형화된 데이터 저장 중: {save_file}")
    
    with open(save_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\n✓ 완료!")
    print(f"  총 {len(data)}건 처리")
    print(f"  {changes_count}건의 차량번호 정형화됨")
    if output_file:
        print(f"  저장 위치: {output_file}")
    else:
        print(f"  원본 파일이 수정되었습니다.")
    
    return True


def print_usage():
    """사용 방법 출력"""
    print("=" * 80)
    print("차량번호 정형화 프로그램")
    print("=" * 80)
    print("\n사용 방법:")
    print("  python 차량번호_정형화.py <CSV파일> [출력파일] [옵션]")
    print("\n예시:")
    print("  # 원본 파일 수정 (백업 자동 생성)")
    print("  python 차량번호_정형화.py \"(신규)주차등록(응답) - 차량_DB 시트.csv\"")
    print("\n  # 새 파일로 저장")
    print("  python 차량번호_정형화.py \"입력.csv\" \"출력.csv\"")
    print("\n  # 상세 출력")
    print("  python 차량번호_정형화.py \"입력.csv\" --verbose")
    print("\n옵션:")
    print("  --verbose, -v    변경된 차량번호 상세 출력")
    print("  --backup         백업 파일 생성 (기본값: 백업 안 함)")
    print("=" * 80)


def main():
    """메인 함수"""
    # 명령줄 인자 파싱
    args = sys.argv[1:]
    
    # 도움말 요청
    if not args or '--help' in args or '-h' in args:
        print_usage()
        return
    
    csv_file = None
    output_file = None
    verbose = False
    backup = False  # 기본값: 백업 생성 안 함
    
    # 인자 파싱
    for arg in args:
        if arg in ['--verbose', '-v']:
            verbose = True
        elif arg == '--backup':
            backup = True
        elif not csv_file:
            csv_file = arg.strip().strip('"')
        elif not output_file:
            output_file = arg.strip().strip('"')
    
    # CSV 파일이 없으면 입력 요청
    if not csv_file:
        print_usage()
        csv_file = input("\nCSV 파일 경로를 입력하세요: ").strip().strip('"')
    
    if not csv_file:
        print("오류: CSV 파일 경로를 입력해주세요.")
        sys.exit(1)
    
    if not Path(csv_file).exists():
        print(f"오류: 파일이 존재하지 않습니다: {csv_file}")
        sys.exit(1)
    
    # 출력 파일이 지정되지 않았고 명령줄 인자가 있으면 자동으로 원본 수정
    # 명령줄 인자가 없을 때만 대화형으로 확인
    if not output_file:
        # 명령줄 인자가 있으면 자동으로 원본 파일 수정 (output_file = None)
        # 명령줄 인자가 없으면 대화형으로 확인
        if len(sys.argv) == 1:  # 명령줄 인자가 없을 때만
            output_option = input("\n원본 파일을 수정하시겠습니까? (y/n, 기본: y): ").strip().lower()
            if output_option == 'n':
                output_file = input("출력 파일명을 입력하세요: ").strip().strip('"')
                if not output_file:
                    path = Path(csv_file)
                    output_file = str(path.parent / f"{path.stem}_정형화{path.suffix}")
        # 명령줄 인자가 있으면 output_file은 None으로 유지 (원본 파일 수정)
    
    # 처리 실행
    print(f"\n처리 시작: {csv_file}")
    success = process_csv_file(csv_file, output_file, backup=backup, verbose=verbose)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

