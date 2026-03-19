from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api.core.config import settings


def utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def app_timezone() -> tzinfo:
    tz_name = settings.APP_TIMEZONE
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        # Windows + missing tzdata fallback: keep Beijing day-boundary behavior.
        if tz_name in {"Asia/Shanghai", "PRC", "Asia/Chongqing", "Asia/Harbin", "Asia/Urumqi"}:
            return timezone(timedelta(hours=8))
        return timezone.utc


def local_now() -> datetime:
    return datetime.now(app_timezone())


def local_date() -> date:
    return local_now().date()


def local_day_bounds_utc(target_date: date | None = None) -> tuple[datetime, datetime]:
    tz = app_timezone()
    day = target_date or local_date()
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    next_start_local = start_local + timedelta(days=1)
    end_local = next_start_local - timedelta(microseconds=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
