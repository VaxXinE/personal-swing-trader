"""Reviewed IDX holiday-gap evidence, not a complete certified exchange calendar."""
from __future__ import annotations

from datetime import date, timedelta

# BEI 2026 holiday announcement (23 Sep 2025), corroborated by the broker notice.
# Only this exact closure interval is reviewed; no other missing session is excused.
IDX_MARCH_2026_CLOSURES = frozenset({
    date(2026, 3, 18), date(2026, 3, 19), date(2026, 3, 20),
    date(2026, 3, 23), date(2026, 3, 24),
})
IDX_MARCH_2026_SOURCE = (
    'https://www.idxchannel.com/market-news/'
    'catat-ini-kalender-libur-bursa-efek-indonesia-2026'
)
IDX_MARCH_2026_REVIEW_VERSION = 'IDX_MARCH_2026_BEI_ANNOUNCEMENT_V1'


def reviewed_idx_gap(market: str, previous: date, current: date) -> bool:
    """Excuse long gaps only if every intervening weekday is a documented closure."""
    if market != 'IDX' or (current - previous).days <= 7:
        return False
    intervening = (
        previous + timedelta(days=offset)
        for offset in range(1, (current - previous).days)
    )
    weekdays = [day for day in intervening if day.weekday() < 5]
    return bool(weekdays) and all(day in IDX_MARCH_2026_CLOSURES for day in weekdays)
