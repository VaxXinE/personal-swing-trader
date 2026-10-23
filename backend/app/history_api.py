"""Read-only private history API; ingestion is an explicit separate CLI operation."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from .config import settings
from .history import HistoryStore, HistoryError

router = APIRouter(prefix='/v1/history', tags=['historical-research'])
store = HistoryStore(settings.db_path.parent / 'history.sqlite')


@router.get('/batches')
def history_batches(limit: int = Query(50, ge=1, le=100)):
    return {'items': store.batches(limit=limit), 'execution_verified': False}


@router.get('/observations/{instrument_id:path}')
def history_observations(instrument_id: str, source: str, price_basis: str,
                         as_of: str | None = None, limit: int = Query(500, ge=1, le=2500)):
    try:
        result = store.read(instrument_id, source=source, price_basis=price_basis,
                            as_of=as_of, limit=limit)
    except HistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result['rows'] == 0:
        raise HTTPException(status_code=404, detail='No observed historical candles for this source and basis')
    return result


@router.get('/actions/{instrument_id:path}')
def history_actions(instrument_id: str, source: str, as_of: str | None = None):
    try:
        return {'items': store.actions(instrument_id, source=source, as_of=as_of),
                'adjustment_applied': False, 'point_in_time_validated': False}
    except HistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
