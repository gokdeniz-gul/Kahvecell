"""Gerçek zamanlı olay yayını (Server-Sent Events için) — case 8.1 bonus.

Basit bir "yayın kanalı" (pub/sub):
  • Sipariş durumu değişince servis `publish("order:<id>", ...)` ve `publish("shop:<id>", ...)` der.
  • Tarayıcıya açık SSE bağlantıları ilgili kanala abonedir; olayı anında alır.

Bellekte çalışır (tek sunucu). Birden çok sunucuda Redis Pub/Sub gibi ortak bir kanal gerekir.
Servisler senkron (thread havuzunda) çalıştığı için olaylar thread-safe şekilde
abonenin asyncio döngüsüne aktarılır.
"""

import asyncio
import json
import threading
from collections import defaultdict
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[tuple[asyncio.Queue, asyncio.AbstractEventLoop]]] = defaultdict(set)
        self._lock = threading.Lock()

    @asynccontextmanager
    async def subscribe(self, channels: Iterable[str]) -> AsyncIterator[asyncio.Queue]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        entry = (queue, asyncio.get_running_loop())
        channels = list(channels)
        with self._lock:
            for channel in channels:
                self._subscribers[channel].add(entry)
        try:
            yield queue
        finally:
            with self._lock:
                for channel in channels:
                    self._subscribers[channel].discard(entry)
                    if not self._subscribers[channel]:
                        del self._subscribers[channel]

    def publish(self, channel: str, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers.get(channel, ()))
        for queue, loop in subscribers:
            try:
                loop.call_soon_threadsafe(_put_nowait_or_drop, queue, event)
            except RuntimeError:
                pass  # abonenin döngüsü kapanmış; bağlantı zaten bitiyor

    def subscriber_count(self, channel: str) -> int:
        with self._lock:
            return len(self._subscribers.get(channel, ()))


def _put_nowait_or_drop(queue: asyncio.Queue, event: dict[str, Any]) -> None:
    if not queue.full():  # yavaş istemci yüzünden bellek şişmesin
        queue.put_nowait(event)


broker = EventBroker()


def format_sse(event: dict[str, Any], *, name: str = "message") -> str:
    """SSE metin formatı: "event: ...\\ndata: {...}\\n\\n" """
    return f"event: {name}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


async def sse_stream(
    channels: list[str], is_disconnected, *, keepalive_seconds: float = 15.0, max_events: int | None = None
) -> AsyncIterator[str]:
    """Kanallara abone olup gelen olayları SSE metni olarak üretir.

    Bağlantı açık kalsın diye belli aralıklarla yorum satırı (": ping") gönderilir.
    """
    sent = 0
    async with broker.subscribe(channels) as queue:
        yield format_sse({"channels": channels}, name="ready")
        while max_events is None or sent < max_events:
            if await is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=keepalive_seconds)
            except TimeoutError:
                yield ": ping\n\n"
                continue
            yield format_sse(event, name=event.get("type", "message"))
            sent += 1


def order_event(event_type: str, order: Any) -> dict[str, Any]:
    return {
        "type": event_type,
        "order_id": order.id,
        "shop_id": order.shop_id,
        "status": order.status,
        "updated_at": order.updated_at,
    }


def publish_order_event(event_type: str, order: Any) -> None:
    event = order_event(event_type, order)
    broker.publish(f"order:{order.id}", event)
    broker.publish(f"shop:{order.shop_id}", event)
