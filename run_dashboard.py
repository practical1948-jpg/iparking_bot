import os
import sys
from pathlib import Path

def main():
    """Run the Streamlit Dashboard"""
    # 프로젝트 루트
    project_root = Path(__file__).resolve().parent
    
    # 가상환경 활성화 체크 (간단히)
    if sys.prefix == sys.base_prefix:
        print("⚠️ Warning: Virtual environment might not be active.")
    
    # Streamlit 실행 명령어
    # src/ui/main.py 실행
    script_path = project_root / "src" / "ui" / "main.py"
    
    if not script_path.exists():
        print(f"❌ Error: {script_path} does not exist.")
        return
    
    print(f"🚀 Launching iParking Dashboard...")
    cmd = f"streamlit run \"{script_path}\""
    os.system(cmd)

if __name__ == "__main__":
    main()
