"""Sipariş QR kodu: case 13.2 formatında içerik + HMAC-SHA256 imza.

QR içeriği:
    { "order_id", "user_id", "shop_id", "created_at" (ISO 8601), "signature" }

İmza nasıl çalışıyor?
    Sunucu, ilk dört alanı sadece kendisinin bildiği gizli bir anahtarla "mühürler" (HMAC).
    QR'daki tek bir karakter bile değişirse (örn. başka bir order_id yazılırsa) mühür tutmaz.
    Gizli anahtarı bilmeyen biri doğru mührü üretemez; yani sahte QR yapılamaz.
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import segno

from app.core.config import settings

SIGNED_FIELDS = ("order_id", "user_id", "shop_id", "created_at")


def format_created_at(value: datetime) -> str:
    """İmzada kullanılan tarih her zaman aynı biçimde yazılmalı: 2026-11-20T14:30:00Z"""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(fields: dict[str, str]) -> bytes:
    # Alan sırası ve boşluklar imzayı değiştirmesin diye her zaman aynı biçimde yazıyoruz.
    return json.dumps(
        {key: fields[key] for key in SIGNED_FIELDS}, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sign(fields: dict[str, str]) -> str:
    key = settings.qr_signing_secret.encode("utf-8")
    return hmac.new(key, _canonical(fields), hashlib.sha256).hexdigest()


def build_payload(order_id: str, user_id: str, shop_id: str, created_at: datetime) -> dict[str, str]:
    fields = {
        "order_id": order_id,
        "user_id": user_id,
        "shop_id": shop_id,
        "created_at": format_created_at(created_at),
    }
    return {**fields, "signature": sign(fields)}


def is_signature_valid(payload: dict[str, Any]) -> bool:
    if not all(isinstance(payload.get(key), str) for key in (*SIGNED_FIELDS, "signature")):
        return False
    expected = sign({key: payload[key] for key in SIGNED_FIELDS})
    # compare_digest: karşılaştırma süresinden ipucu sızmasın (timing attack).
    return hmac.compare_digest(expected, payload["signature"])


def to_content(payload: dict[str, str]) -> str:
    """QR'a gömülen metin (dükkânın okuyucusu tam olarak bunu okur)."""
    return json.dumps(payload, separators=(",", ":"))


def to_image_data_url(content: str) -> str:
    """QR görseli: tarayıcı adres çubuğuna yapıştırınca açılan PNG (data URL)."""
    return segno.make(content, error="m").png_data_uri(scale=6, border=2)
