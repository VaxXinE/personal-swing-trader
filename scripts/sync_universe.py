"""Refresh candidate universe explicitly; no secrets, no auto-trading, no undocumented endpoints.

Examples:
  python scripts/sync_universe.py --markets US CRYPTO
  python scripts/sync_universe.py --markets IDX --idx-csv ~/Downloads/idx-saham.csv
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.universe import sync_discovery, DiscoveryError


def main() -> int:
    parser = argparse.ArgumentParser(description='Sync market discovery shortlist, not verified liquid universe')
    parser.add_argument('--markets', nargs='+', choices=('US','IDX','CRYPTO'), default=['US','CRYPTO'])
    parser.add_argument('--us-limit', type=int, default=24)
    parser.add_argument('--crypto-limit', type=int, default=18)
    parser.add_argument('--idx-limit', type=int, default=35)
    parser.add_argument('--idx-csv', type=Path, help='Exported IDX stock listing CSV (Kode, Nama Perusahaan, Papan Pencatatan)')
    args = parser.parse_args()
    try:
        result = sync_discovery(args.markets, us_limit=args.us_limit,
                                crypto_limit=args.crypto_limit, idx_limit=args.idx_limit,
                                idx_csv=args.idx_csv)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result['errors'] else 0
    except DiscoveryError as exc:
        print('Discovery configuration error:', exc, file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
