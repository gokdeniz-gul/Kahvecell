"""Konum hesapları: iki nokta arası mesafe (Haversine) ve hızlı ön eleme için "kutu"."""

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088  # Dünya'nın ortalama yarıçapı


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Dünya yüzeyinde iki nokta arasındaki kuş uçuşu mesafe (km).

    Düz bir haritada Pisagor ile hesaplasaydık Dünya'nın yuvarlaklığını yok saymış olurduk;
    Haversine, küre üzerindeki en kısa yolu (büyük daire) hesaplar.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


def bounding_box(lat: float, lng: float, radius_km: float) -> BoundingBox:
    """Merkezin etrafında yarıçapı içine alan kare.

    Veritabanı bu kareyle (enlem/boylam index'i sayesinde) uzaktaki dükkânları hızlıca eler;
    kalan az sayıda dükkân için gerçek mesafe Haversine ile hesaplanır.
    """
    lat_delta = math.degrees(radius_km / EARTH_RADIUS_KM)
    # Kutuplara yaklaştıkça boylam çizgileri birbirine yaklaşır; boylam payını buna göre büyütüyoruz.
    lng_delta = math.degrees(radius_km / (EARTH_RADIUS_KM * max(math.cos(math.radians(lat)), 1e-6)))
    return BoundingBox(
        min_lat=lat - lat_delta,
        max_lat=lat + lat_delta,
        min_lng=lng - lng_delta,
        max_lng=lng + lng_delta,
    )
