from datetime import UTC, datetime, timedelta


def fixed_window_start(now: datetime, window_seconds: int) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    epoch = int(now.timestamp())
    start_epoch = (epoch // window_seconds) * window_seconds
    return datetime.fromtimestamp(start_epoch, tz=UTC)


def fixed_window_reset_at(window_start: datetime, window_seconds: int) -> datetime:
    return window_start + timedelta(seconds=window_seconds)
