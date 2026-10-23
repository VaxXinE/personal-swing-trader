"""Read-only private history API; ingestion is an explicit separate CLI operation."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from .config import settings
from .history import HistoryStore, HistoryError
from .archive_backtest import replay_from_archive, ArchiveNotFound, SnapshotMismatch
from .registry import get_instruments

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


@router.get('/backtests/{instrument_id:path}')
def replay_archived_history(
    instrument_id: str,
    source: str = Query(..., min_length=3, max_length=64),
    price_basis: str = Query(..., min_length=3, max_length=40),
    strategy: str = Query('PULLBACK', pattern='^(PULLBACK|BREAKOUT)$'),
    horizon: int = Query(10, ge=2, le=20),
    as_of: str | None = Query(None, max_length=40),
    limit: int = Query(2500, ge=1, le=2500),
    expected_snapshot_sha256: str | None = Query(None, pattern='^[0-9a-f]{64}$'),
):
    """Offline-only archive replay; no provider access or archive mutation."""
    instrument = next((item for item in get_instruments(settings.data_mode)
                       if item.instrument_id == instrument_id), None)
    if instrument is None:
        raise HTTPException(404, 'Unknown instrument in current registry')
    try:
        return replay_from_archive(
            store, instrument, mode=settings.data_mode, source=source,
            price_basis=price_basis, strategy=strategy, horizon=horizon,
            as_of=as_of, limit=limit,
            expected_snapshot_sha256=expected_snapshot_sha256,
        )
    except ArchiveNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except SnapshotMismatch as exc:
        raise HTTPException(409, str(exc)) from exc
    except HistoryError as exc:
        raise HTTPException(422, str(exc)) from exc
