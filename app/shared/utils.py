from __future__ import annotations

from datetime import datetime, timezone


def now_sydney() -> datetime:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Australia/Sydney"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


def parse_datetime(s: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(s, fmt)
