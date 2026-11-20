"""Örnek veri (seed) betiği: paketler, İstanbul'da 6 dükkân + menüleri, test kullanıcıları.

Çalıştırma (backend klasöründe, sanal ortam açıkken):

    python -m scripts.seed

Betik güvenle tekrar çalıştırılabilir: eksik olan admin hesabını ekler; test müşterisi
zaten varsa başka bir şey eklemez.
Her şey tek bir transaction içinde yazılır; yarıda hata olursa hiçbir kayıt yazılmaz.
"""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (tüm tablolar Base'e kaydolsun)
from app.core.database import SessionLocal
from app.core.migrations import upgrade_database
from app.models import Payment, Plan, Product, Shop, ShopPhoto, Subscription, User
from app.models.enums import PaymentStatus, PlanType, ProductCategory, UserRole

CUSTOMER_PHONE = "5551234567"
SHOP_OWNER_PHONE = "5559876543"
ADMIN_PHONE = "5550000000"

# Fiyatlar kuruş cinsinden (89,99 TL → 8999).
PLANS = [
    dict(plan_type=PlanType.STARTER, name="Starter", monthly_price_kurus=8999,
         monthly_credits=10, guest_passes=0, has_priority=False),
    dict(plan_type=PlanType.PREMIUM, name="Premium", monthly_price_kurus=14999,
         monthly_credits=20, guest_passes=2, has_priority=False),
    dict(plan_type=PlanType.UNLIMITED, name="Unlimited", monthly_price_kurus=24999,
         monthly_credits=None, guest_passes=5, has_priority=True),
]

HOT = ProductCategory.HOT_COFFEE
COLD = ProductCategory.COLD_COFFEE
TEA = ProductCategory.TEA

# Dükkân adları hayalîdir; koordinatlar semtlerin gerçek konumlarıdır.
# Ürünler: (ad, açıklama, kategori, fiyat_TL)
SHOPS = [
    dict(
        name="Moda Kavurma Evi", city="İstanbul",
        address="Caferağa Mah. Moda Cad., Kadıköy",
        latitude=40.9862, longitude=29.0262,
        opens_at=time(8, 0), closes_at=time(23, 0), rating=4.7, rating_count=312,
        products=[
            ("Espresso", "Tek shot, günün çekirdeği", HOT, 110),
            ("Cappuccino", "Espresso, buharlı süt ve bol köpük", HOT, 165),
            ("Flat White", "Çift shot ristretto, ince süt köpüğü", HOT, 180),
            ("Filtre Kahve", "V60 ile demlenmiş tek köken", HOT, 140),
            ("Cold Brew", "18 saat soğuk demleme", COLD, 190),
        ],
    ),
    dict(
        name="Çarşı Kahvecisi", city="İstanbul",
        address="Sinanpaşa Mah. Çarşı içi, Beşiktaş",
        latitude=41.0434, longitude=29.0053,
        opens_at=time(7, 30), closes_at=time(22, 0), rating=4.4, rating_count=528,
        products=[
            ("Türk Kahvesi", "Közde pişirilmiş, lokum ile", HOT, 95),
            ("Espresso", "Tek shot", HOT, 100),
            ("Americano", "Espresso ve sıcak su", HOT, 135),
            ("Latte", "Espresso ve bol buharlı süt", HOT, 160),
            ("Demleme Çay", "İnce belli bardakta", TEA, 40),
        ],
    ),
    dict(
        name="Karaköy Liman Kahve", city="İstanbul",
        address="Kemankeş Karamustafa Paşa Mah., Karaköy",
        latitude=41.0229, longitude=28.9775,
        opens_at=time(8, 0), closes_at=time(20, 0), rating=4.8, rating_count=874,
        products=[
            ("Espresso", "Çift shot, Etiyopya çekirdeği", HOT, 125),
            ("Cortado", "Espresso ve eşit miktar süt", HOT, 155),
            ("Flat White", "Çift shot ristretto", HOT, 195),
            ("Iced Latte", "Buzlu espresso ve soğuk süt", COLD, 205),
            ("Cold Brew", "Portakal kabuğu notalı", COLD, 210),
        ],
    ),
    dict(
        name="Cihangir Köşe", city="İstanbul",
        address="Firuzağa Mah. Akarsu Yokuşu, Beyoğlu",
        latitude=41.0318, longitude=28.9829,
        opens_at=time(9, 0), closes_at=time(23, 30),
        rating=4.5, rating_count=401,
        products=[
            ("Türk Kahvesi", "Orta şekerli servis edilebilir", HOT, 110),
            ("Cappuccino", "İtalyan usulü", HOT, 170),
            ("Mocha", "Espresso, bitter çikolata ve süt", HOT, 190),
            ("Chai Latte", "Baharatlı çay ve süt", TEA, 165),
        ],
    ),
    dict(
        name="Teşvikiye Brew Bar", city="İstanbul",
        address="Teşvikiye Mah. Abdi İpekçi Cad., Şişli",
        latitude=41.0503, longitude=28.9934,
        opens_at=time(8, 0), closes_at=time(21, 0), rating=4.6, rating_count=650,
        products=[
            ("Espresso", "Tek köken, günlük değişir", HOT, 135),
            ("Latte", "Yulaf sütü seçeneğiyle", HOT, 200),
            ("Filtre Kahve", "Chemex ile iki kişilik", HOT, 175),
            ("Iced Americano", "Buzlu espresso ve su", COLD, 170),
            ("Espresso Tonic", "Tonik, espresso ve limon", COLD, 220),
        ],
    ),
    dict(
        name="Kuzguncuk Bostan Kahve", city="İstanbul",
        address="Kuzguncuk Mah. İcadiye Cad., Üsküdar",
        latitude=41.0362, longitude=29.0316,
        # Bilerek kısa çalışma saati: "açık/kapalı" filtresini denemek için.
        opens_at=time(10, 0), closes_at=time(18, 0), rating=4.3, rating_count=189,
        products=[
            ("Türk Kahvesi", "Bakır cezvede", HOT, 90),
            ("Dibek Kahvesi", "Taş dibekte dövülmüş", HOT, 105),
            ("Americano", "Espresso ve sıcak su", HOT, 130),
            ("Demleme Çay", "Semaver çayı", TEA, 35),
        ],
    ),
]


def tl_to_kurus(tl: float) -> int:
    return round(tl * 100)


# Dükkân fotoğrafları: frontend/public/images/shops/ (kaynak ve lisans: CREDITS.md)
# (dosya adı, ekran okuyucu açıklaması); ilki kapak görselidir.
SHOP_PHOTOS = {
    "Moda Kavurma Evi": [
        ("moda-1.jpg", "Portafiltrede taze öğütülmüş kahve"),
        ("moda-2.jpg", "Demleme barında filtre kahve ekipmanları"),
        ("moda-3.jpg", "Ahşap tahta üzerinde kahve tadım seti"),
    ],
    "Çarşı Kahvecisi": [
        ("carsi-1.jpg", "Işıklı CAFE tabelalı dükkân içi"),
        ("carsi-2.jpg", "Yuvarlak tepside farklı kahveler"),
        ("carsi-3.jpg", "Fincanda köpüklü sade kahve"),
    ],
    "Karaköy Liman Kahve": [
        ("karakoy-1.jpg", "Geniş, aydınlık kafe salonu"),
        ("karakoy-2.jpg", "Koyu zeminde latte art'lı fincan"),
        ("karakoy-3.jpg", "Bardakta soğuk kahve"),
    ],
    "Cihangir Köşe": [
        ("cihangir-1.jpg", "Pencere kenarında masa ve bitkiler"),
        ("cihangir-2.jpg", "Latte art'lı iki fincan tutan eller"),
        ("cihangir-3.jpg", "Taş sokakta açık hava kafe masaları"),
    ],
    "Teşvikiye Brew Bar": [
        ("tesvikiye-1.jpg", "Raflı ve sarkıt lambalı kahve barı"),
        ("tesvikiye-2.jpg", "Yeşil bitkiler arasında latte'ler"),
        ("tesvikiye-3.jpg", "Ahşap masada buzlu latte"),
    ],
    "Kuzguncuk Bostan Kahve": [
        ("kuzguncuk-1.jpg", "Bitkilerle çevrili bahçe kafe"),
        ("kuzguncuk-2.jpg", "Ahşap sandalyeli kafe salonu"),
        ("kuzguncuk-3.jpg", "Fincanda köpüklü sade kahve"),
    ],
}
SHOP_PHOTO_BASE_URL = "/images/shops/"


def ensure_shop_photos(db: Session) -> None:
    """Fotoğrafı olmayan dükkânlara fotoğraflarını ekler (önceden seed edilmiş veritabanları için de)."""
    added = 0
    for shop_name, photos in SHOP_PHOTOS.items():
        shop = db.scalar(select(Shop).where(Shop.name == shop_name))
        if shop is None or shop.photos:
            continue
        shop.photos = [
            ShopPhoto(url=SHOP_PHOTO_BASE_URL + file, alt_text=alt, position=index)
            for index, (file, alt) in enumerate(photos)
        ]
        shop.image_url = SHOP_PHOTO_BASE_URL + photos[0][0]  # kapak görseli (liste kartları için)
        added += 1
    if added:
        db.commit()
        print(f"Fotoğraf eklendi      : {added} dükkân")


def ensure_admin(db: Session) -> None:
    """Admin hesabı API'den oluşturulamaz (güvenlik); sadece bu betikle eklenir.
    Ana seed'den ayrı tutuldu: seed daha önce çalıştırılmış olsa da admin eklenebilsin."""
    if db.scalar(select(User).where(User.phone_number == ADMIN_PHONE)):
        return
    db.add(
        User(
            phone_number=ADMIN_PHONE,
            is_phone_verified=True,
            full_name="Test Admin",
            email="admin@kahvecell.test",
            role=UserRole.ADMIN,
        )
    )
    db.commit()
    print(f"Admin eklendi        : telefon {ADMIN_PHONE}, OTP 1234")


def seed(db: Session) -> None:
    ensure_admin(db)
    if db.scalar(select(User).where(User.phone_number == CUSTOMER_PHONE)):
        print("Seed verisi zaten var, başka bir şey eklenmedi.")
        return

    # 1) Paketler (daha önce eklenmiş olanlar atlanır)
    plans: dict[PlanType, Plan] = {}
    for data in PLANS:
        plan = db.scalar(select(Plan).where(Plan.plan_type == data["plan_type"]))
        if plan is None:
            plan = Plan(**data)
            db.add(plan)
        plans[data["plan_type"]] = plan

    # 2) Kullanıcılar
    customer = User(
        phone_number=CUSTOMER_PHONE,
        is_phone_verified=True,
        full_name="Test Müşteri",
        email="musteri@kahvecell.test",
        role=UserRole.CUSTOMER,
        preferences={"coffee_types": ["LATTE", "TURKISH"], "allergens": []},
    )
    owner = User(
        phone_number=SHOP_OWNER_PHONE,
        is_phone_verified=True,
        full_name="Test Dükkân Sahibi",
        email="dukkan@kahvecell.test",
        role=UserRole.SHOP_OWNER,
    )
    db.add_all([customer, owner])

    # 3) Dükkânlar ve menüleri
    for data in SHOPS:
        shop_fields = {key: value for key, value in data.items() if key != "products"}
        products = data["products"]
        shop = Shop(**shop_fields, owner=owner)
        shop.products = [
            Product(name=name, description=desc, category=cat, price_kurus=tl_to_kurus(price))
            for name, desc, cat, price in products
        ]
        db.add(shop)

    # 4) Müşteriye aktif Starter abonelik + onu satın aldığı başarılı ödeme kaydı
    starter = plans[PlanType.STARTER]
    now = datetime.now(UTC)
    subscription = Subscription(
        user=customer,
        plan=starter,
        remaining_credits=starter.monthly_credits,
        remaining_guest_passes=starter.guest_passes,
        started_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(subscription)
    db.add(
        Payment(
            user=customer,
            plan=starter,
            subscription=subscription,
            transaction_id="SEED-TXN-0001",
            status=PaymentStatus.SUCCESS,
            amount_kurus=starter.monthly_price_kurus,
            card_last4="4242",
        )
    )

    db.commit()
    product_count = db.scalar(select(func.count()).select_from(Product))
    print(f"Eklendi: {len(PLANS)} paket, {len(SHOPS)} dükkân, {product_count} ürün, "
          "2 kullanıcı, 1 aktif abonelik.")
    print(f"Müşteri girişi       : telefon {CUSTOMER_PHONE}, OTP 1234")
    print(f"Dükkân sahibi girişi : telefon {SHOP_OWNER_PHONE}, OTP 1234")


def main() -> None:
    upgrade_database()  # sunucu hiç açılmamış olsa da şema hazır olsun
    with SessionLocal() as db:
        seed(db)
        ensure_shop_photos(db)


if __name__ == "__main__":
    main()
