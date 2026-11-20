"""Basit rate limiting: aynı IP'den belli sürede en fazla N istek (case 4.4).

Neden gerekli? Biri saniyede yüzlerce "SMS kodu gönder" veya "ödeme dene" isteği atarsa
hem SMS maliyeti doğar hem de kaba kuvvet (brute force) denemesi yapılabilir.

Bellekte tutulur: tek sunucu için yeterli. Birden çok sunucuya geçilirse sayaçlar
Redis gibi ortak bir yere taşınmalı.
"""

import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: float) -> float | None:
        """İsteği say. Limit aşıldıysa kaç saniye sonra tekrar denenebileceğini döner."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return window_seconds - (now - hits[0])
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def rate_limit(scope: str, per_minute: Callable[[], int]) -> Callable[[Request], None]:
    """Router'a eklenecek dependency. Örn: Depends(rate_limit("auth", lambda: 10))"""

    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "unknown"
        retry_after = limiter.hit(f"{scope}:{client_ip}", per_minute(), 60)
        if retry_after is not None:
            seconds = math.ceil(retry_after)
            raise TooManyRequestsError(
                f"Çok fazla istek gönderdiniz. {seconds} saniye sonra tekrar deneyin.",
                code="RATE_LIMITED",
                details={"retry_after_seconds": seconds},
                headers={"Retry-After": str(seconds)},
            )

    return dependency


auth_rate_limit = rate_limit("auth", lambda: settings.auth_rate_limit_per_minute)
payment_rate_limit = rate_limit("payment", lambda: settings.payment_rate_limit_per_minute)
