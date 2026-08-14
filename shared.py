import sys
from pathlib import Path

temp_file = "temp.csv"
version = "1.3"

def get_executing_dir():
    path = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    return str(path)
