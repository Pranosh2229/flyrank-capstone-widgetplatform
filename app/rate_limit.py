"""In-process sliding-window rate limiter.

The submission endpoint needs two independent limits -- per IP and per
widget -- and the widget id only exists inside the POST body, which
slowapi's request-based key functions can't key on cleanly. A small
dependency-free limiter keyed on whatever string the caller passes keeps
both limits simple, synchronous, and easy to reason about under a burst
test.

Not distributed -- fine for a single-process capstone; a real multi-worker
deployment would move this to Redis, noted in the README's limitations.
"""

import re
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _parse_rate(rate: str) -> tuple[int, int]:
        match = re.match(r"(\d+)/(second|minute|hour)", rate)
        if not match:
            raise ValueError(f"bad rate spec: {rate}")
        count = int(match.group(1))
        unit = match.group(2)
        window = {"second": 1, "minute": 60, "hour": 3600}[unit]
        return count, window

    def allow(self, key: str, rate: str) -> bool:
        limit, window_seconds = self._parse_rate(rate)
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


ip_limiter = SlidingWindowLimiter()
widget_limiter = SlidingWindowLimiter()
