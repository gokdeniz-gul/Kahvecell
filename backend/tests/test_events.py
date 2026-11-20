"""Gerçek zamanlı sipariş bildirimi (SSE) — case 8.1 bonus."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.events import EventBroker, broker, format_sse, sse_stream
from tests.test_orders import customer, karakoy, owner, place_order, set_status  # noqa: F401  (fixture'lar)
from tests.test_subscriptions import subscribe

pytestmark = pytest.mark.usefixtures("plans", "fixed_clock")


@pytest.fixture(autouse=True)
def fast_keepalive(monkeypatch):
    monkeypatch.setattr(settings, "sse_keepalive_seconds", 0.2)


def read_events(lines, count: int) -> list[tuple[str, dict]]:
    """SSE satırlarından sıradaki `count` olayı (ping'leri atlayarak) oku.

    `lines` tek bir iterator olmalı: httpx akışı sadece bir kez okunabilir.
    """
    events, name = [], None
    for line in lines:
        if line.startswith("event: "):
            name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            events.append((name, json.loads(line.removeprefix("data: "))))
            if len(events) == count:
                return events
    return events


# ---------- Yayın kanalı (unit) ----------


def test_broker_delivers_only_to_subscribed_channel() -> None:
    async def scenario():
        broker = EventBroker()
        async with broker.subscribe(["order:1"]) as mine, broker.subscribe(["order:2"]) as other:
            broker.publish("order:1", {"type": "order.updated", "status": "READY"})
            await asyncio.sleep(0)  # call_soon_threadsafe'in çalışması için
            assert mine.get_nowait()["status"] == "READY"
            assert other.empty()
        assert broker.subscriber_count("order:1") == 0  # bağlantı bitince abonelik silinir

    asyncio.run(scenario())


def test_sse_stream_sends_ready_ping_and_events() -> None:
    async def scenario():
        async def never_disconnected():
            return False

        stream = sse_stream(["order:x"], never_disconnected, keepalive_seconds=0.05, max_events=1)
        assert (await anext(stream)).startswith("event: ready")
        assert await anext(stream) == ": ping\n\n"  # olay yokken bağlantıyı canlı tutar
        broker.publish("order:x", {"type": "order.updated", "status": "ACCEPTED"})
        event = await anext(stream)
        assert event.startswith("event: order.updated") and '"ACCEPTED"' in event

    asyncio.run(scenario())


def test_format_sse() -> None:
    assert format_sse({"a": 1}, name="ready") == 'event: ready\ndata: {"a": 1}\n\n'


# ---------- Endpoint'ler ----------


def test_stream_requires_valid_token(client: TestClient) -> None:
    response = client.get("/api/v1/orders/123/events", params={"token": "bozuk"})

    assert response.status_code == 401


def test_customer_cannot_stream_someone_elses_order(client, customer, karakoy) -> None:  # noqa: F811
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    from tests.conftest import register_and_login

    stranger = register_and_login(client, "5554445566")["access_token"]

    response = client.get(f"/api/v1/orders/{order_id}/events", params={"token": stranger})

    assert response.status_code == 404


def test_customer_receives_live_status_update(client, customer, owner, karakoy) -> None:  # noqa: F811
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    token = customer["headers"]["Authorization"].removeprefix("Bearer ")

    with client.stream("GET", f"/api/v1/orders/{order_id}/events", params={"token": token}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = response.iter_lines()
        assert read_events(lines, 1)[0][0] == "ready"

        set_status(client, owner["headers"], order_id, "ACCEPTED")  # dükkân kabul ediyor

        name, event = read_events(lines, 1)[0]
        assert name == "order.updated"
        assert (event["order_id"], event["status"]) == (order_id, "ACCEPTED")


def test_shop_owner_is_notified_of_new_orders(client, customer, owner, karakoy) -> None:  # noqa: F811
    subscribe(client, customer["headers"], "STARTER")
    token = owner["headers"]["Authorization"].removeprefix("Bearer ")

    with client.stream("GET", "/api/v1/orders/incoming/events", params={"token": token}) as response:
        lines = response.iter_lines()
        assert read_events(lines, 1)[0][0] == "ready"

        order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

        name, event = read_events(lines, 1)[0]
        assert name == "order.created"
        assert event["order_id"] == order_id


def test_customer_cannot_open_shop_stream(client, customer) -> None:  # noqa: F811
    token = customer["headers"]["Authorization"].removeprefix("Bearer ")

    assert client.get("/api/v1/orders/incoming/events", params={"token": token}).status_code == 403
