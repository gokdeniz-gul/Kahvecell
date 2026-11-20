"""Yapılandırılmış (structured) loglama — case 4.4.

Her isteğe bir kimlik (request_id) verilir; o istek sırasında yazılan tüm log satırları
bu kimliği taşır. Böylece bir hata bildirildiğinde ilgili tüm satırlar tek aramayla bulunur.

LOG_FORMAT=json  → her satır tek bir JSON nesnesi (log toplama sistemleri için)
LOG_FORMAT=text  → geliştirmede okunaklı düz metin
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Log kaydına "extra" ile eklenen ve JSON'a taşınacak alanlar
_EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "client_ip")

access_logger = logging.getLogger("app.access")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        entry.update({key: getattr(record, key) for key in _EXTRA_FIELDS if hasattr(record, key)})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(log_format: str = "text", level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


async def request_context_middleware(request: Request, call_next):
    """Her isteğe kimlik ver, süresini ölç ve tek satırlık erişim kaydı yaz."""
    incoming = request.headers.get("X-Request-ID", "")
    # Dışarıdan gelen kimliği sadece makulse kabul et (log'a zararlı içerik girmesin).
    request_id = incoming if 0 < len(incoming) <= 64 and incoming.replace("-", "").isalnum() else uuid.uuid4().hex
    token = request_id_var.set(request_id)
    request.state.request_id = request_id  # hata cevabına da eklensin diye
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        # Beklenmeyen hatayı istek kimliğiyle birlikte burada logla; cevabı global handler üretir.
        logging.getLogger("app.errors").exception("Beklenmeyen hata: %s %s", request.method, request.url.path)
        raise
    finally:
        access_logger.info(
            "%s %s %s",
            request.method,
            request.url.path,
            status,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "client_ip": request.client.host if request.client else None,
            },
        )
        request_id_var.reset(token)
