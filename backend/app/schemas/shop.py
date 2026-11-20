from datetime import time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import ProductCategory


class ShopSort(StrEnum):
    DISTANCE = "distance"  # konum gönderildiyse varsayılan
    RATING = "rating"  # konum yoksa varsayılan
    NAME = "name"


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    category: ProductCategory
    price_kurus: int
    is_available: bool
    image_url: str | None

    @computed_field
    def price_tl(self) -> float:
        return self.price_kurus / 100


class ShopSummary(BaseModel):
    """Liste ve harita için dükkân bilgisi."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    address: str
    city: str
    latitude: float
    longitude: float
    opens_at: time
    closes_at: time
    is_open_now: bool
    rating: float
    rating_count: int
    image_url: str | None
    distance_km: float | None = Field(
        default=None, description="Sadece konum (lat, lng) gönderildiyse dolu; kuş uçuşu mesafe"
    )


class ShopPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    alt_text: str


class ShopDetail(ShopSummary):
    """Dükkân detay sayfası: bilgiler + fotoğraflar + menü."""

    phone: str | None
    photos: list[ShopPhotoResponse] = Field(description="Galeri; ilk fotoğraf kapak görselidir")
    menu: list[ProductResponse]


class ShopListResponse(BaseModel):
    items: list[ShopSummary]
    total: int
    offset: int
    limit: int
