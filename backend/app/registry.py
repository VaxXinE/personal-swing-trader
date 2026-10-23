"""User-editable instrument registry with validation, no arbitrary endpoints."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .domain import Instrument

REGISTRY_FILE=Path(__file__).resolve().parents[2]/'config'/'universe.json'

def get_instruments()->tuple[Instrument,...]:
    if not REGISTRY_FILE.is_file():raise ValueError('Missing config/universe.json')
    raw=json.loads(REGISTRY_FILE.read_text(encoding='utf-8'))
    items=raw.get('instruments')
    if not isinstance(items,list) or not 1<=len(items)<=250:
        raise ValueError('Instrument registry must contain 1 to 250 items')
    result=[];seen=set()
    for row in items:
        i=Instrument(**row)
        if i.market not in ('US','IDX','CRYPTO') or i.kind not in ('EQUITY','SPOT'):
            raise ValueError('Unsupported market/instrument kind')
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,40}',i.provider_symbol):
            raise ValueError('Invalid provider symbol')
        if not re.fullmatch(r'(US|IDX|CRYPTO):[A-Z0-9_-]{2,30}:[A-Z0-9.-]{1,30}',i.instrument_id):
            raise ValueError('Invalid canonical instrument_id')
        if i.instrument_id in seen:raise ValueError('Duplicate instrument_id')
        if not i.instrument_id.startswith(i.market+':'):raise ValueError('Market mismatch')
        seen.add(i.instrument_id);result.append(i)
    return tuple(result)
