import os
import sys
from pathlib import Path

def main():
    """Run the Parking Bot"""
    project_root = Path(__file__).resolve().parent
    
    # Check for venv
    if sys.prefix == sys.base_prefix:
        print("⚠️ Warning: Virtual environment might not be active.")
    
    script_path = project_root / "src" / "core" / "bot.py"
    
    if not script_path.exists():
        print(f"❌ Error: {script_path} does not exist.")
        return
    
    print(f"🚀 Launching Parking Bot...")
    print(f"   Mode: Polling (Waiting for Dashboard Input)")
    
    try:
        # Run the bot
        os.system(f"python \"{script_path}\"")
    except KeyboardInterrupt:
        print("\nBot stopped.")

if __name__ == "__main__":
    main()
