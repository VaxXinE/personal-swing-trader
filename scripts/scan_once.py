"""Suitable for private cron at 07:30 Asia/Jakarta; never uses unfinished candles."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.config import settings
from app.rules import ScreenerConfig
from app.service import scan
from app.storage import Store

if __name__=='__main__':
    result=scan(Store(settings.db_path),settings.data_mode,
                ScreenerConfig(name='Daily EOD Scan',strategy='BOTH'))
    print(f"Scan {result['run_id']}: {result['count']} candidates; {len(result['errors'])} errors; mode={settings.data_mode}")
    if result['errors']: sys.exit(2)
