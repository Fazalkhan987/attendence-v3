from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings

TZ = ZoneInfo(settings.TIMEZONE)


def now_local() -> datetime:
    return datetime.now(TZ)


def today_local() -> date:
    return now_local().date()


def combine_local(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=TZ)


def to_local(dt: datetime) -> datetime:
    return dt.astimezone(TZ)
