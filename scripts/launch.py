"""Cross-platform development launcher: python scripts/launch.py [--live] [--host ...]"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'backend'
sys.path.insert(0,str(BACKEND))

def main():
    from app import config
    config.load_local_env()
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Use real public market providers; requires optional yfinance package.')
    parser.add_argument('--host',default=os.getenv('SWING_HOST','127.0.0.1'))
    parser.add_argument('--port',type=int,default=int(os.getenv('SWING_PORT','8000')))
    args=parser.parse_args()
    if args.live:os.environ['SWING_DATA_MODE']='live'
    os.environ['SWING_HOST']=args.host
    # Settings must be built AFTER CLI/environment overrides, not during config import.
    config.settings=config.Settings()
    token=os.environ.get('SWING_API_TOKEN','')
    if args.host not in ('127.0.0.1','localhost','::1') and len(token)<32:
        raise SystemExit('ERROR: Non-loopback requires SWING_API_TOKEN (32+ random characters). Use VPN/Tailscale, not public port forwarding.\n'+
                         'Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"')
    import uvicorn
    print('Personal Swing Intelligence — ',os.environ.get('SWING_DATA_MODE','demo').upper(),flush=True)
    print(f'Open: http://{args.host}:{args.port}/  (browser interface)',flush=True)
    uvicorn.run('app.main:app',host=args.host,port=args.port,app_dir=str(BACKEND),log_level='info')

if __name__=='__main__':main()
