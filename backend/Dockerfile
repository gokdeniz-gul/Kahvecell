# KahveCell API — FastAPI
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Önce sadece bağımlılıklar: kod değişince bu katman önbellekten gelir, build hızlanır.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts

# Root olmayan kullanıcıyla çalış (güvenlik)
RUN useradd --create-home --uid 1000 kahvecell && mkdir -p /data && chown kahvecell /data
USER kahvecell

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"

# Demo verisi (test hesapları, dükkânlar) varsayılan olarak eklenir; üretimde SEED_DEMO_DATA=false.
# Migration'lar uygulama açılırken zaten çalışır.
ENV SEED_DEMO_DATA=true

# --proxy-headers: nginx arkasında gerçek istemci IP'si (rate limit için) X-Forwarded-For'dan okunur.
# Backend dışarıya port açmadığı için sadece nginx'e güvenmek güvenli.
# Tek süreç (worker): canlı bildirim kanalı (SSE) bellekte tutuluyor.
CMD ["sh", "-c", "[ \"$SEED_DEMO_DATA\" = \"false\" ] || python -m scripts.seed; exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
