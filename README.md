# ☕ KahveCell

**Dijital kahve abonelik platformu.** Operatör aboneleri aylık paket alır, haritadan yakınındaki anlaşmalı dükkânı bulur, kahvesini özelleştirip sipariş verir ve kasada imzalı QR koduyla teslim alır.

> Turkcell Geleceği Yazanlar — Prompt Mühendisliği eğitimi bitirme case çalışması.

| | |
|---|---|
| **Backend** | Python 3.12+ · FastAPI · SQLAlchemy 2.0 · SQLite · PyJWT · pytest |
| **Frontend** | React 19 · Vite · React Router · TanStack Query · Zustand · axios |
| **Harita** | Leaflet · OpenStreetMap (API anahtarı gerektirmez) |

---

## Özellikler

- **Kayıt / giriş:** GSM numarası + SMS OTP (simülasyon, kod `1234`), JWT access + refresh token, rol bazlı erişim (Müşteri / Dükkân Sahibi / Admin)
- **Abonelik:** Starter · Premium · Unlimited; satın alma, yükseltme (fark ödenir, anında), düşürme (gelecek dönem), iptal (dönem sonuna kadar geçerli), aylık yenileme
- **Mobil ödeme simülasyonu:** `4242 4242 4242 4242` başarılı, `4000 0000 0000 0002` reddedilir; tüm denemeler ödeme geçmişine kaydedilir, kartın sadece son 4 hanesi saklanır
- **Dükkân keşfi:** Haversine ile mesafeye göre sıralama, yarıçap filtresi, Türkçe karakter duyarsız arama, puan ve "şu an açık" filtreleri, harita
- **Sipariş:** boy / şeker / süt / ek shot özelleştirme, abonelik hakkından atomik düşüm, durum takibi, favori sipariş tekrarı
- **İmzalı QR:** case 13.2 formatında içerik + HMAC-SHA256 imza; sahte, değiştirilmiş ya da başka dükkâna ait QR reddedilir, teslim sadece QR ile yapılır
- **Dükkân akışı:** gelen siparişler (Unlimited aboneler öncelikli), Kabul → Hazırlanıyor → Hazır → Teslim

---

## Hızlı başlangıç

Gereksinimler: **Python 3.12+**, **Node.js 20+**

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
python -m scripts.seed          # paketler, 6 İstanbul dükkânı, test hesapları
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- **Swagger dokümantasyonu: http://127.0.0.1:8000/docs**

### 2. Frontend (ayrı bir terminalde)

```bash
cd frontend
npm install
npm run dev
```

- Uygulama: **http://localhost:5173**
- Geliştirmede `/api` istekleri Vite proxy ile backend'e yönlendirilir; ayrıca ayar gerekmez.

### Test hesapları

Tüm hesaplarda doğrulama kodu **`1234`**.

| Rol | Telefon | Not |
|---|---|---|
| Müşteri | `5551234567` | Aktif Starter aboneliği var |
| Dükkân sahibi | `5559876543` | 6 dükkânın sahibi; sipariş durumunu günceller |
| Admin | `5550000000` | Kullanıcı listesi, rol değiştirme |

### Testler

```bash
cd backend && pytest          # 142 test
cd frontend && npm run lint && npm run build
```

---

## Mimari

```
┌──────────────┐  /api/v1 (JSON)  ┌──────────────────────────────────────────┐
│ React (Vite) │ ───────────────► │ FastAPI                                  │
│  Router      │                  │  api/v1 (router)   → isteği al, doğrula  │
│  React Query │ ◄─────────────── │  services          → iş kuralları        │
│  Zustand     │ {success,data,   │  repositories      → veritabanı erişimi  │
└──────────────┘  error}          │  models (SQLAlchemy) ─► SQLite           │
                                  └──────────────────────────────────────────┘
```

**Katmanlı yapı:** endpoint'ler HTTP ile, servisler iş kurallarıyla, repository'ler veritabanıyla ilgilenir. Servisler HTTP bilmez; `NotFoundError` gibi anlamlı hatalar fırlatır, global handler bunları standart cevaba çevirir.

**Standart cevap formatı** (tüm endpoint'ler):

```json
{ "success": false, "data": null, "error": { "code": "NO_CREDITS_LEFT", "message": "Bu ayki kahve hakkınız bitti...", "details": {} } }
```

### Veritabanı

`users` · `plans` · `subscriptions` · `payments` · `shops` · `products` · `orders` · `order_items` · `otp_requests` · `refresh_tokens`

- UUID primary key'ler (QR içeriği UUID ister; sıralı ID tahmin edilebilir)
- Foreign key, CHECK ve UNIQUE kuralları veritabanı seviyesinde; SQLite'ta foreign key zorlaması açık
- Para **kuruş** cinsinden tam sayı (float yuvarlama hatası yok), tarihler UTC
- Kullanıcı başına tek geçerli abonelik (partial unique index)
- Sipariş anındaki fiyat `order_items`'a kopyalanır; ürün fiyatı değişse de eski fiş değişmez

### Önemli kararlar

| Konu | Karar | Neden |
|---|---|---|
| Ödeme akışı | Önce `POST /payments/process` → `transaction_id` → `POST /subscriptions` | Case 12: transaction ID ile eşleştirme; ödeme tek kullanımlık ve kullanıcı/paket/tutara göre doğrulanır |
| Tutar | Sunucu hesaplar (yeni abonelikte tam fiyat, yükseltmede fark) | İstemci tutarı değiştiremez |
| Kahve hakkı düşümü | Tek SQL `UPDATE ... WHERE remaining_credits > 0` | Çift tıklamada bile hak iki kez harcanamaz (race condition yok) |
| Yakınlık sorgusu | Enlem/boylam index'iyle kutu ön elemesi + Haversine | SQLite'ta spatial index yok; PostgreSQL'e geçilirse PostGIS |
| Refresh token | Rastgele, veritabanında SHA-256 özeti, tek kullanımlık (rotation) | Çalınan eski token tekrar kullanılırsa kullanıcının tüm oturumları kapanır |
| QR imzası | HMAC-SHA256, JWT'den ayrı anahtar | Anahtarı bilmeyen geçerli QR üretemez; bir anahtar sızarsa diğeri güvende |
| Saat | Türkiye sabit UTC+3 | 2016'dan beri yaz saati yok; Windows'ta tz veritabanı gerektirmez |

---

## API özeti

Tam liste ve canlı deneme için: **`/docs`** (Swagger, otomatik üretilir).

| Grup | Endpoint'ler |
|---|---|
| Auth | `POST /auth/register` · `/login` · `/verify-otp` · `/refresh` · `/logout` |
| Kullanıcı | `GET` / `PATCH /users/me` · `GET /users` (admin) · `PATCH /users/{id}/role` (admin) |
| Abonelik | `GET /subscriptions/plans` · `POST /subscriptions` · `GET` / `PATCH` / `DELETE /subscriptions/me` |
| Ödeme | `POST /payments/process` · `GET /payments/me` |
| Dükkân | `GET /shops?lat=&lng=&radius_km=&q=&open_now=` · `GET /shops/{id}` · `GET /shops/{id}/menu` |
| Sipariş | `POST /orders` · `GET /orders/{id}` · `GET /orders/history` · `GET /orders/incoming` · `PATCH /orders/{id}/status` · `POST /orders/verify-qr` · `POST /orders/{id}/reorder` |

---

## Güvenlik

- Refresh token ve OTP kodları veritabanında **özet (hash)** olarak saklanır; kart numarası hiç saklanmaz ve loglanmaz
- `/auth/*` ve `/payments/process` için **IP başına dakikalık istek sınırı** (429 + `Retry-After`)
- Güvenlik başlıkları (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`), API cevaplarında `Cache-Control: no-store`
- CORS sadece tanımlı frontend adreslerine açık
- `ENVIRONMENT=production` iken varsayılan, yer tutucu, kısa ya da birbirinin aynı JWT/QR anahtarlarıyla **uygulama açılmaz**
- Doğrulama hatalarında gönderilen değer cevaba geri yazılmaz (örn. kart numarası)

> ⚠️ `config.py` içindeki varsayılan anahtarlar **yalnızca geliştirme** içindir. Üretimde `.env` ile değiştirin:
> `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## Bilinen sınırlar ve yol haritası

- **Migration:** şema şimdilik açılışta `create_all` ile oluşuyor; şema değişince `kahvecell.db` silinip seed tekrar çalıştırılmalı. Sıradaki adım: Alembic.
- **Dükkân sahibi paneli** henüz frontend'de yok; sipariş durumu ve QR doğrulama Swagger'dan yapılıyor. QR ekranı durumu 5 sn'de bir yenileyerek takip ediyor; WebSocket/SSE ile anlık bildirim planlandı.
- Token'lar tarayıcıda `localStorage`'da; üretim için httpOnly cookie değerlendirilebilir.
- Rate limit sayaçları bellekte (tek sunucu); çoklu sunucuda Redis'e taşınmalı.
- Docker Compose ve GitHub Actions (CI) eklenmedi.

---

## Proje yapısı

```
kahvecell/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # endpoint'ler (router)
│   │   ├── core/          # ayarlar, veritabanı, güvenlik, QR, hata yönetimi, rate limit
│   │   ├── models/        # SQLAlchemy tabloları
│   │   ├── schemas/       # Pydantic istek/cevap şemaları
│   │   ├── services/      # iş kuralları
│   │   ├── repositories/  # veritabanı sorguları
│   │   └── utils/         # Haversine, Türkçe arama normalizasyonu
│   ├── scripts/seed.py    # örnek veri
│   └── tests/             # pytest
└── frontend/
    └── src/
        ├── api/           # axios istemcisi + endpoint fonksiyonları
        ├── components/    # layout, harita, durum ekranları
        ├── pages/         # 8 sayfa
        ├── hooks/ store/ lib/ styles/
        └── router.jsx
```
