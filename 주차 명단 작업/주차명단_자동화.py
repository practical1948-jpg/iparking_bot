"""
주차 명단 자동화 스크립트
CSV 파일의 모든 데이터를 성함 기준 가나다 순으로 정렬하고 프린트합니다.

=== 중요 규칙 ===
1. A4 용지 한 장에 모든 데이터가 들어가야 함 (절대 위반 불가)
2. 이를 위해 글자 크기, 패딩, 마진 등이 최적화되어 있음
3. 글자 크기를 더 키우거나 레이아웃 변경 시 A4 한 장을 넘을 수 있음
4. 위 규칙을 위반하는 요구가 있으면 사용자에게 경고해야 함
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict


def read_csv_file(file_path: str) -> List[Dict[str, str]]:
    """CSV 파일을 읽어서 딕셔너리 리스트로 반환합니다."""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # CSV 파일의 첫 줄을 헤더로 사용
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"오류: CSV 파일 읽기 실패: {e}")
        sys.exit(1)


def sort_by_name(data: List[Dict[str, str]], 
                name_column: str = None) -> List[Dict[str, str]]:
    """
    이름을 가나다 순으로 정렬합니다.
    
    Args:
        data: CSV 데이터 리스트
        name_column: 이름 컬럼명 (None이면 자동 감지 시도)
    """
    if not data:
        return []
    
    # 컬럼명 자동 감지
    if name_column is None:
        possible_columns = ['성함', '이름', '성명', 'name', '이름(한글)']
        for col in possible_columns:
            if col in data[0]:
                name_column = col
                break
    
    if name_column is None:
        print("경고: 이름 컬럼을 찾을 수 없습니다. 정렬하지 않습니다.")
        return data
    
    # 가나다 순 정렬 (한글 정렬)
    sorted_data = sorted(data, key=lambda x: str(x.get(name_column, '')))
    return sorted_data


def print_parking_list(data: List[Dict[str, str]]):
    """주차 명단을 출력합니다."""
    if not data:
        print("등록 대상자가 없습니다.")
        return
    
    print("\n" + "="*80)
    print("주차 등록 대상자 명단 (가나다 순)")
    print("="*80)
    
    # 출력할 컬럼 선택 (번호, 상태, 처리시간 제외)
    if data:
        all_columns = list(data[0].keys())
        # 출력할 컬럼: 성함, 차량번호만 (또는 사용자가 원하는 컬럼)
        display_columns = ['성함', '차량번호']
        # 실제 존재하는 컬럼만 사용
        display_columns = [col for col in display_columns if col in all_columns]
        
        if not display_columns:
            display_columns = all_columns
        
        # 헤더 출력
        header = " | ".join([f"{col:20}" for col in display_columns])
        print(f"{'번호':>4} | {header}")
        print("-"*80)
        
        # 데이터 출력
        for idx, row in enumerate(data, 1):
            values = [f"{str(row.get(col, '')):20}" for col in display_columns]
            print(f"{idx:>4} | " + " | ".join(values))
    
    print("="*80)
    print(f"\n총 {len(data)}명")


def save_to_file(data: List[Dict[str, str]], output_file: str = "주차명단_정렬.csv"):
    """정렬된 명단을 CSV 파일로 저장합니다."""
    if not data:
        print("저장할 데이터가 없습니다.")
        return
    
    try:
        # 성함과 차량번호만 저장 (또는 원본 컬럼 유지)
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            # 원본 컬럼 유지하되, 성함과 차량번호를 앞에 배치
            fieldnames = ['성함', '차량번호']
            # 나머지 컬럼 추가 (번호, 상태, 처리시간 제외)
            for col in data[0].keys():
                if col not in fieldnames and col not in ['번호', '상태', '처리시간']:
                    fieldnames.append(col)
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                # 필요한 컬럼만 포함
                filtered_row = {k: v for k, v in row.items() if k in fieldnames}
                writer.writerow(filtered_row)
        print(f"\n정렬된 명단이 저장되었습니다: {output_file}")
        return output_file
    except Exception as e:
        print(f"오류: 파일 저장 실패: {e}")
        return None


def get_initial_consonant(name: str) -> str:
    """한글 이름에서 초성을 추출합니다."""
    if not name or len(name) == 0:
        return '기타'
    
    first_char = name[0]
    
    # 한글인지 확인
    if '가' <= first_char <= '힣':
        # 한글 유니코드: 가(0xAC00) ~ 힣(0xD7A3)
        # 초성 = (유니코드 - 0xAC00) // 588
        code = ord(first_char) - 0xAC00
        initial_index = code // 588
        
        # 초성 리스트: ㄱ, ㄲ, ㄴ, ㄷ, ㄸ, ㄹ, ㅁ, ㅂ, ㅃ, ㅅ, ㅆ, ㅇ, ㅈ, ㅉ, ㅊ, ㅋ, ㅌ, ㅍ, ㅎ
        initials = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        
        if 0 <= initial_index < len(initials):
            return initials[initial_index]
    
    # 한글이 아니면 첫 글자 그대로 반환
    return first_char.upper() if first_char.isalpha() else '기타'


def group_by_initial(data: List[Dict[str, str]], name_column: str = '성함') -> Dict[str, List[Dict[str, str]]]:
    """데이터를 초성별로 그룹화합니다."""
    grouped = {}
    
    for row in data:
        name = str(row.get(name_column, '')).strip()
        initial = get_initial_consonant(name)
        
        if initial not in grouped:
            grouped[initial] = []
        grouped[initial].append(row)
    
    # 초성 순서대로 정렬 (ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅅ, ㅇ, ㅈ, ㅊ, ㅋ, ㅌ, ㅍ, ㅎ)
    initial_order = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    sorted_grouped = {}
    
    for initial in initial_order:
        if initial in grouped:
            sorted_grouped[initial] = grouped[initial]
    
    # 기타 초성도 추가
    for initial in grouped:
        if initial not in sorted_grouped:
            sorted_grouped[initial] = grouped[initial]
    
    return sorted_grouped


def save_to_html(data: List[Dict[str, str]], output_file: str = "주차명단_정렬.html"):
    """정렬된 명단을 HTML 파일로 저장합니다."""
    if not data:
        print("저장할 데이터가 없습니다.")
        return None
    
    try:
        from datetime import datetime
        
        # 출력할 컬럼 선택
        all_columns = list(data[0].keys())
        display_columns = ['성함', '차량번호']
        display_columns = [col for col in display_columns if col in all_columns]
        
        if not display_columns:
            display_columns = all_columns
        
        # 초성별로 그룹화
        name_column = '성함' if '성함' in all_columns else display_columns[0]
        grouped_data = group_by_initial(data, name_column)
        
        # 현재 날짜 가져오기
        current_date = datetime.now().strftime("%Y. %m. %d")
        
        html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주차 등록 대상자 명단</title>
    <style>
        :root {{
            --ink: #111;
            --grid: rgba(17, 17, 17, 0.75);
            --grid-soft: rgba(17, 17, 17, 0.45);
            --zebra: #fafafa;
            --initial-bg: #f2f3f5;
        }}
        html, body {{
            margin: 0;
            padding: 0;
            background: #fff;
            color: var(--ink);
        }}
        body {{
            font-family: 'Malgun Gothic', '맑은 고딕', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif;
            padding: 8px;
        }}
        .container {{
            width: 100%;
            max-width: 210mm;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin: 0 0 10px 0;
        }}
        h1 {{
            font-size: 22pt;
            font-weight: 900;
            margin: 0 0 2px 0;
            letter-spacing: -0.3px;
        }}
        .date {{
            font-size: 14pt;
            margin: 0;
            color: rgba(17,17,17,0.85);
        }}
        .tables-container {{
            display: flex;
            gap: 0;
            width: 100%;
        }}
        table {{
            flex: 1;
            border-collapse: collapse;
            border: 1.2px solid var(--grid);
            font-size: 11pt;
            line-height: 1.15;
            table-layout: fixed;
            width: 100%;
        }}
        table:not(:first-child) {{
            border-left: none;
        }}
        thead {{
            display: none;
        }}
        td {{
            border: 0.7px solid var(--grid-soft);
            padding: 0 4px;
            height: 5mm;
            line-height: 5mm;
            vertical-align: middle;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: clip;
        }}
        tbody tr:nth-child(even) {{
            background-color: #fff;
        }}
        tbody tr:nth-child(odd) {{
            background-color: var(--zebra);
        }}
        .number {{
            width: 9mm;
            font-weight: 900;
            text-align: center;
            background-color: var(--initial-bg);
            border-right: 0.7px solid var(--grid-soft);
        }}
        .name {{
            width: 40%;
            text-align: center;
            font-weight: 800;
        }}
        .car-number {{
            width: 60%;
            text-align: left;
            font-variant-numeric: tabular-nums;
            font-feature-settings: "tnum";
            font-family: 'Consolas', 'Cascadia Mono', 'Roboto Mono', ui-monospace, monospace;
            letter-spacing: 0.2px;
        }}
        @media print {{
            * {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            @page {{
                size: A4;
                margin: 7mm;
            }}
            body {{
                padding: 0;
            }}
            .container {{
                width: 210mm;
                max-width: 210mm;
                margin: 0 auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>주차 등록 대상자 명단</h1>
            <div class="date">{current_date}</div>
        </div>"""
        
        # 모든 데이터를 하나의 리스트로 만들기 (초성 정보 포함)
        all_rows = []
        for initial, group_data in grouped_data.items():
            # 해당 초성의 데이터 추가 (첫 번째 행에 초성 정보 포함)
            for idx, row in enumerate(group_data):
                all_rows.append({
                    'type': 'data',
                    'row': row,
                    'initial': initial,
                    'is_first_in_group': idx == 0,
                    'group_size': len(group_data)
                })
        
        # 열 개수 결정 (기본 4열: 가독성과 1장 충족 균형)
        num_columns = 4
        rows_per_column = (len(all_rows) + num_columns - 1) // num_columns
        
        # 여러 열로 나누기
        html_content += '\n        <div class="tables-container">'
        
        for col_idx in range(num_columns):
            start_idx = col_idx * rows_per_column
            end_idx = min((col_idx + 1) * rows_per_column, len(all_rows))
            column_rows = all_rows[start_idx:end_idx]
            
            html_content += f'\n            <table>'
            html_content += f'\n                <thead>'
            html_content += f'\n                    <tr>'
            html_content += f'\n                        <th class="number">번호</th>'
            for col in display_columns:
                html_content += f'\n                        <th>{col}</th>'
            html_content += f'\n                    </tr>'
            html_content += f'\n                </thead>'
            html_content += f'\n                <tbody>'
            
            # 현재 그룹의 초성과 rowspan 계산
            prev_initial = None
            
            for idx, item in enumerate(column_rows):
                row = item['row']
                initial = item['initial']
                
                # 이전 행과 초성이 다르면 새로운 그룹 시작
                is_new_group = (prev_initial != initial)
                
                if is_new_group:
                    # 현재 열에서 이 그룹이 얼마나 포함되는지 계산
                    # 같은 초성을 가진 연속된 행의 개수를 세어야 함
                    group_count = 1
                    for j in range(idx + 1, len(column_rows)):
                        if column_rows[j]['initial'] == initial:
                            group_count += 1
                        else:
                            break
                    
                    html_content += f'\n                    <tr>'
                    html_content += f'\n                        <td class="number" rowspan="{group_count}">{initial}</td>'
                    for col in display_columns:
                        value = str(row.get(col, '')).strip()
                        if col == '성함':
                            html_content += f'\n                        <td class="name">{value}</td>'
                        else:
                            html_content += f'\n                        <td class="car-number">{value}</td>'
                    html_content += '\n                    </tr>'
                    
                    prev_initial = initial
                else:
                    # 같은 그룹의 나머지 행
                    html_content += f'\n                    <tr>'
                    for col in display_columns:
                        value = str(row.get(col, '')).strip()
                        if col == '성함':
                            html_content += f'\n                        <td class="name">{value}</td>'
                        else:
                            html_content += f'\n                        <td class="car-number">{value}</td>'
                    html_content += '\n                    </tr>'
            
            html_content += f'\n                </tbody>'
            html_content += f'\n            </table>'
        
        html_content += f'\n        </div>'
        html_content += f"""
    </div>
</body>
</html>"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nHTML 파일이 저장되었습니다: {output_file}")
        return output_file
    except Exception as e:
        print(f"오류: HTML 파일 저장 실패: {e}")
        return None


def open_html_file(html_file: str):
    """HTML 파일을 기본 브라우저로 엽니다."""
    try:
        import webbrowser
        import os
        
        if not Path(html_file).exists():
            print(f"오류: 파일이 존재하지 않습니다: {html_file}")
            return False
        
        # 절대 경로로 변환
        abs_path = os.path.abspath(html_file)
        file_url = f"file:///{abs_path.replace(os.sep, '/')}"
        
        webbrowser.open(file_url)
        print(f"브라우저에서 HTML 파일을 열었습니다.")
        return True
    except Exception as e:
        print(f"오류: HTML 파일 열기 실패: {e}")
        return False


def print_to_printer(output_file: str):
    """파일을 프린터로 출력합니다."""
    try:
        import subprocess
        import os
        
        if not Path(output_file).exists():
            print(f"오류: 파일이 존재하지 않습니다: {output_file}")
            return False
        
        # Windows에서 Excel이나 메모장으로 열어서 프린트
        # 방법 1: 메모장으로 프린트
        try:
            subprocess.run(['notepad', '/p', output_file], check=False, timeout=5)
            print("프린트 작업을 시작했습니다.")
            return True
        except:
            pass
        
        # 방법 2: 기본 프로그램으로 열기
        try:
            os.startfile(output_file, 'print')
            print("프린트 작업을 시작했습니다.")
            return True
        except:
            pass
        
        print("프린트를 위해 파일을 열었습니다. 수동으로 프린트해주세요.")
        return False
    except Exception as e:
        print(f"프린트 오류: {e}")
        return False


def print_usage():
    """사용 방법 출력"""
    print("=" * 80)
    print("주차 명단 자동화 프로그램")
    print("=" * 80)
    print("\n사용 방법:")
    print("  python 주차명단_자동화.py <CSV파일> [옵션]")
    print("\n예시:")
    print("  # 기본 실행 (대화형 모드)")
    print("  python 주차명단_자동화.py \"(신규)주차등록(응답) - 차량_DB 시트.csv\"")
    print("\n  # 자동 모드 (HTML만 생성)")
    print("  python 주차명단_자동화.py \"입력.csv\" --html-only")
    print("\n  # 자동 모드 (CSV와 HTML 모두 생성)")
    print("  python 주차명단_자동화.py \"입력.csv\" --auto")
    print("\n옵션:")
    print("  --html-only    HTML 파일만 자동 생성 (브라우저 자동 열기)")
    print("  --auto         CSV와 HTML 모두 자동 생성")
    print("  --no-browser   브라우저 자동 열기 안 함")
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
    html_only = False
    auto_mode = False
    open_browser_flag = True
    
    # 인자 파싱
    for arg in args:
        if arg == '--html-only':
            html_only = True
            auto_mode = True
        elif arg == '--auto':
            auto_mode = True
        elif arg == '--no-browser':
            open_browser_flag = False
        elif not csv_file:
            csv_file = arg.strip().strip('"')
    
    # CSV 파일이 없으면 입력 요청
    if not csv_file:
        if sys.stdin.isatty():
            print_usage()
            csv_file = input("\nCSV 파일 경로를 입력하세요: ").strip().strip('"')
        else:
            print("오류: CSV 파일 경로를 입력해주세요.")
            print_usage()
            sys.exit(1)
    
    if not csv_file:
        print("오류: CSV 파일 경로를 입력해주세요.")
        sys.exit(1)
    
    if not Path(csv_file).exists():
        print(f"오류: 파일이 존재하지 않습니다: {csv_file}")
        sys.exit(1)
    
    # CSV 파일 읽기
    print(f"\nCSV 파일 읽는 중: {csv_file}")
    data = read_csv_file(csv_file)
    print(f"총 {len(data)}건의 데이터를 읽었습니다.")
    
    # 가나다 순 정렬
    print("성함 기준 가나다 순 정렬 중...")
    sorted_data = sort_by_name(data)
    
    # 결과 출력
    if not auto_mode:
        print_parking_list(sorted_data)
    
    output_file = None
    html_file = None
    
    # 자동 모드가 아니면 대화형으로 진행
    if not auto_mode:
        # 파일로 저장
        save_option = input("\n정렬된 명단을 CSV 파일로 저장하시겠습니까? (y/n): ").strip().lower()
        if save_option == 'y' or save_option == '':
            default_file = "주차명단_정렬.csv"
            output_file_input = input(f"저장할 파일명 (기본: {default_file}): ").strip()
            output_file = output_file_input if output_file_input else default_file
            output_file = save_to_file(sorted_data, output_file)
        
        # HTML 파일 생성
        html_option = input("\nHTML 파일로 저장하시겠습니까? (y/n): ").strip().lower()
        if html_option == 'y' or html_option == '':
            default_html = "주차명단_정렬.html"
            html_file_input = input(f"저장할 HTML 파일명 (기본: {default_html}): ").strip()
            html_file = html_file_input if html_file_input else default_html
            html_file = save_to_html(sorted_data, html_file)
            
            # HTML 파일을 브라우저로 열기
            if html_file and open_browser_flag:
                open_browser = input("브라우저에서 HTML 파일을 열까요? (y/n): ").strip().lower()
                if open_browser == 'y' or open_browser == '':
                    open_html_file(html_file)
    else:
        # 자동 모드
        if not html_only:
            # CSV 파일 저장
            default_file = "주차명단_정렬.csv"
            output_file = save_to_file(sorted_data, default_file)
        
        # HTML 파일 생성
        default_html = "주차명단_정렬.html"
        html_file = save_to_html(sorted_data, default_html)
        
        # 브라우저 자동 열기
        if html_file and open_browser_flag:
            print("\n브라우저에서 HTML 파일을 엽니다...")
            open_html_file(html_file)
    
    print("\n✓ 작업 완료!")


if __name__ == "__main__":
    main()

