from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic

from backend.app.schemas.rate_limit import RateLimitResult


RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

_request_history: dict[str, deque[float]] = defaultdict(deque)
_history_lock = Lock()


def check_rate_limit(
    identifier: str,
    current_time: float | None = None,
) -> RateLimitResult:
    now = monotonic() if current_time is None else current_time
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    with _history_lock:
        request_times = _request_history[identifier]

        while (
            request_times
            and request_times[0] <= window_start
        ):
            request_times.popleft()

        if len(request_times) >= RATE_LIMIT_REQUESTS:
            retry_after_seconds = max(
                1,
                ceil(
                    request_times[0]
                    + RATE_LIMIT_WINDOW_SECONDS
                    - now
                ),
            )

            return RateLimitResult(
                allowed=False,
                limit=RATE_LIMIT_REQUESTS,
                remaining=0,
                retry_after_seconds=retry_after_seconds,
            )

        request_times.append(now)

        return RateLimitResult(
            allowed=True,
            limit=RATE_LIMIT_REQUESTS,
            remaining=(
                RATE_LIMIT_REQUESTS - len(request_times)
            ),
            retry_after_seconds=0,
        )


def reset_rate_limit(identifier: str | None = None) -> None:
    with _history_lock:
        if identifier is None:
            _request_history.clear()
            return

        _request_history.pop(identifier, None)
