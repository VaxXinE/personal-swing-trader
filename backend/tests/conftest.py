import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
os.environ['SWING_DATA_MODE']='demo'
os.environ['SWING_DB_PATH']=str(ROOT/'data'/'test-isolated.db')
