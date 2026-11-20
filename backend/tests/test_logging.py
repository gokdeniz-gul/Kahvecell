"""Yapılandırılmış loglama ve istek kimliği (case 4.4)."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter, RequestIdFilter, request_id_var
from app.main import app


def test_every_response_has_request_id(client: TestClient) -> None:
    first = client.get("/api/v1/health").headers["X-Request-ID"]
    second = client.get("/api/v1/health").headers["X-Request-ID"]

    assert first and second and first != second


def test_incoming_request_id_is_reused(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "istemci-123"})

    assert response.headers["X-Request-ID"] == "istemci-123"


@pytest.mark.parametrize("bad_id", ["a b <script>", "x" * 200, "id;DROP TABLE"])
def test_malicious_request_id_is_replaced(client: TestClient, bad_id: str) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": bad_id})

    assert response.headers["X-Request-ID"] != bad_id


def test_access_log_has_structured_fields(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/api/v1/shops")

    record = next(r for r in caplog.records if r.name == "app.access")
    assert (record.method, record.path, record.status) == ("GET", "/api/v1/shops", 200)
    assert record.duration_ms >= 0


def test_json_formatter_outputs_one_json_object() -> None:
    token = request_id_var.set("abc123")
    try:
        record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "merhaba %s", ("dünya",), None)
        record.status = 200
        RequestIdFilter().filter(record)
        line = JsonFormatter().format(record)
    finally:
        request_id_var.reset(token)

    entry = json.loads(line)
    assert entry["message"] == "merhaba dünya"
    assert entry["request_id"] == "abc123"
    assert entry["status"] == 200
    assert entry["level"] == "INFO"


def test_unexpected_error_returns_500_with_request_id() -> None:
    @app.get("/api/v1/_test-boom")
    def boom() -> None:
        raise RuntimeError("gizli iç detay")

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/_test-boom")
    finally:
        app.router.routes.pop()  # test endpoint'ini kaldır

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "gizli iç detay" not in response.text  # iç bilgi sızmıyor
    assert body["error"]["details"]["request_id"] == response.headers.get("X-Request-ID", body["error"]["details"]["request_id"])
