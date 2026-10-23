"""Check exchange daily session marker is distinct from conservative EOD availability."""
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo
import pytest
from app.providers import equity_session_markers, ProviderError


def test_us_dst_regular_close_not_the_ready_guard():
    close,ready=equity_session_markers('US',date(2026,10,22))
    assert close.isoformat()=='2026-10-22T20:00:00+00:00'  # 4 pm EDT
    assert ready.isoformat()=='2026-10-22T21:00:00+00:00'  # 5 pm EDT
    assert close<ready


def test_us_standard_time_regular_close():
    close,ready=equity_session_markers('US',date(2026,11,3))
    assert close.isoformat()=='2026-11-03T21:00:00+00:00'  # 4 pm EST
    assert ready.isoformat()=='2026-11-03T22:00:00+00:00'


def test_idx_close_is_not_negotiated_market_ready_guard():
    close,ready=equity_session_markers('IDX',date(2026,10,22))
    assert close.isoformat()=='2026-10-22T09:02:00+00:00'
    assert ready.isoformat()=='2026-10-22T09:30:00+00:00'


def test_unexpected_market_rejected():
    with pytest.raises(ValueError):
        equity_session_markers('CRYPTO',date(2026,10,22))


def test_yahoo_bar_timestamp_not_reused_from_availability_guard(monkeypatch):
    """Provider's session-date daily row must get the closing marker, not 5 PM."""
    import sys
    from types import SimpleNamespace
    import pandas as pd
    from app import providers
    from app.domain import INSTRUMENTS

    frame=pd.DataFrame({'Open':[100.], 'High':[103.], 'Low':[99.],
                        'Close':[102.], 'Volume':[10000.]},
                       index=pd.DatetimeIndex(['2026-10-22'],tz='America/New_York'))
    monkeypatch.setitem(sys.modules,'yfinance',SimpleNamespace(Ticker=lambda symbol:SimpleNamespace(history=lambda **kwargs:frame)))
    actual_datetime=providers.datetime

    class FakeClock(actual_datetime):
        instant=datetime(2026,10,22,21,5,tzinfo=timezone.utc)

        @classmethod
        def now(cls,tz=None):
            return cls.instant if tz is None else cls.instant.astimezone(tz)

    monkeypatch.setattr(providers,'datetime',FakeClock)
    us=next(x for x in INSTRUMENTS if x.symbol=='MSFT')
    bars,quote=providers.fetch_yfinance(us)
    assert len(bars)==1 and quote is None
    assert bars[0].at=='2026-10-22T20:00:00Z'

    FakeClock.instant=datetime(2026,10,22,20,45,tzinfo=timezone.utc)
    with pytest.raises(ProviderError,match='No FINAL'):
        providers.fetch_yfinance(us)
