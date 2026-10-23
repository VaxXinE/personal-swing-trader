"""User-editable instrument registry with validation, no arbitrary endpoints."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .domain import Instrument

REGISTRY_FILE=Path(__file__).resolve().parents[2]/'config'/'universe.json'

def get_instruments(mode: str = "demo")->tuple[Instrument,...]:
    if not REGISTRY_FILE.is_file():raise ValueError('Missing config/universe.json')
    raw=json.loads(REGISTRY_FILE.read_text(encoding='utf-8'))
    items=raw.get('instruments')
    if not isinstance(items,list) or not 1<=len(items)<=250:
        raise ValueError('Instrument registry must contain 1 to 250 items')
    if mode not in ('demo', 'live'):
        raise ValueError('Invalid registry mode')
    # Use dynamic discovery only in LIVE mode. DEMO stays a deterministic small fixture.
    # Manual instruments take precedence over discovered candidates for stable IDs.
    if mode == 'live':
        from .universe import _read_snapshot, SNAPSHOT_PATH
        snap = _read_snapshot(SNAPSHOT_PATH)
        discovered = snap['instruments']
        if len(discovered) > 225:
            raise ValueError('Dynamic universe exceeds safe cap')
        items = items + discovered
    result=[];seen=set();seen_provider=set()
    for row in items:
        i=Instrument(**row)
        if i.market not in ('US','IDX','CRYPTO') or i.kind not in ('EQUITY','SPOT'):
            raise ValueError('Unsupported market/instrument kind')
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,40}',i.provider_symbol):
            raise ValueError('Invalid provider symbol')
        if not re.fullmatch(r'(US|IDX|CRYPTO):[A-Z0-9_-]{2,30}:[A-Z0-9.-]{1,30}',i.instrument_id):
            raise ValueError('Invalid canonical instrument_id')
        if i.instrument_id in seen or (i.market,i.provider_symbol) in seen_provider:
            continue  # manual source wins on canonical ID or vendor-symbol alias
        if not i.instrument_id.startswith(i.market+':'):raise ValueError('Market mismatch')
        seen.add(i.instrument_id);seen_provider.add((i.market,i.provider_symbol));result.append(i)
        if len(result)>250:raise ValueError('Universe exceeds 250 total instruments; reduce sync limits')
    return tuple(result)
