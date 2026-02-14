from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import get_settings


def _get_app_tz():
    tz_name = get_settings().APP_TIMEZONE
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # 兜底为东八区，避免时区字符串异常导致主流程失败。
        return timezone(timedelta(hours=8))


def app_now() -> datetime:
    """返回应用时区的当前时间。"""
    return datetime.now(_get_app_tz())


def to_app_tz(value: datetime | None) -> datetime | None:
    """把任意 datetime 转换到应用时区。"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_get_app_tz())
