"""Çalışan bir KahveCell sistemine karşı uçtan uca duman testi (smoke test).

Sadece Python standart kütüphanesi kullanır; ek kurulum gerekmez.

    python backend/scripts/smoke_test.py                       # http://localhost:8080 (Docker)
    python backend/scripts/smoke_test.py http://localhost:5173 # Vite geliştirme sunucusu

Senaryo: sağlık → dükkânlar → kayıt/OTP → ödeme → abonelik → sipariş → SSE ile canlı durum
         (dükkân sahibi kabul eder) → QR doğrulama → teslim.
"""

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from random import randint

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/") + "/api/v1"
OWNER_PHONE = "5559876543"  # seed betiğindeki dükkân sahibi


def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    request = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())["data"]
    except urllib.error.HTTPError as error:
        raise SystemExit(f"❌ {method} {path} → {error.code}: {error.read().decode()}") from None


def login(phone: str, *, register: bool = False) -> str:
    call("POST", "/auth/register" if register else "/auth/login", {"phone_number": phone})
    return call("POST", "/auth/verify-otp", {"phone_number": phone, "code": "1234"})["access_token"]


def ok(message: str) -> None:
    print(f"✅ {message}")


def main() -> None:
    print(f"Hedef: {BASE}")
    call("GET", "/health")
    ok("API ayakta")

    shops = call("GET", "/shops", None)["items"]
    assert len(shops) >= 5, "Seed verisi yüklenmemiş"
    ok(f"{len(shops)} dükkân listelendi")

    customer = login(f"53{randint(10_000_000, 99_999_999)}", register=True)
    ok("Yeni müşteri kaydı + OTP doğrulama")

    card = {"card_holder": "SMOKE TEST", "card_number": "4242424242424242",
            "expiry_month": 12, "expiry_year": 2035, "cvc": "123"}
    payment = call("POST", "/payments/process", {"plan_type": "STARTER", "card": card}, customer)
    subscription = call("POST", "/subscriptions", {"plan_type": "STARTER", "transaction_id": payment["transaction_id"]}, customer)
    assert subscription["remaining_credits"] == 10
    ok("Ödeme (4242…) + Starter abonelik")

    open_shops = call("GET", "/shops?open_now=true")["items"]
    if not open_shops:
        print("⚠️  Şu an açık dükkân yok (İstanbul saatiyle gece); sipariş adımları atlandı.")
        return
    shop = open_shops[0]
    product = next(p for p in call("GET", f"/shops/{shop['id']}/menu") if p["is_available"])
    order = call("POST", "/orders", {"shop_id": shop["id"], "product_id": product["id"]}, customer)
    assert call("GET", "/subscriptions/me", None, customer)["remaining_credits"] == 9
    ok(f"Sipariş verildi ({product['name']} @ {shop['name']}), 1 kahve hakkı düştü")

    # Canlı durum: müşteri SSE akışını dinlerken dükkân siparişi kabul ediyor.
    events: list[str] = []

    def listen() -> None:
        url = f"{BASE}/orders/{order['id']}/events?token={customer}"
        with urllib.request.urlopen(url, timeout=15) as stream:
            for raw in stream:
                line = raw.decode().strip()
                if line.startswith("event: "):
                    events.append(line.removeprefix("event: "))
                    if events[-1] == "order.updated":
                        return

    listener = threading.Thread(target=listen, daemon=True)
    listener.start()
    time.sleep(1)
    owner = login(OWNER_PHONE)
    started = time.perf_counter()
    call("PATCH", f"/orders/{order['id']}/status", {"status": "ACCEPTED"}, owner)
    listener.join(timeout=10)
    assert "order.updated" in events, f"SSE olayı ulaşmadı (proxy tamponluyor olabilir): {events}"
    ok(f"SSE canlı bildirim {round((time.perf_counter() - started) * 1000)} ms içinde ulaştı")

    for status in ("PREPARING", "READY"):
        call("PATCH", f"/orders/{order['id']}/status", {"status": status}, owner)
    verified = call("POST", "/orders/verify-qr", {"qr_content": order["qr"]["content"]}, owner)
    assert verified["valid"] and verified["can_complete"]
    ok("Dükkân QR kodu doğruladı")

    fake = {**order["qr"]["payload"], "signature": "0" * 64}
    try:
        call("POST", "/orders/verify-qr", {"qr_content": json.dumps(fake)}, owner)
        raise SystemExit("❌ Sahte QR kabul edildi!")
    except SystemExit as error:
        if "QR_SIGNATURE_INVALID" not in str(error):
            raise
    ok("Sahte QR reddedildi")

    done = call("PATCH", f"/orders/{order['id']}/status", {"status": "COMPLETED", "qr_content": order["qr"]["content"]}, owner)
    assert done["status"] == "COMPLETED"
    ok("Sipariş QR ile teslim edildi")
    print("\n🎉 Uçtan uca senaryo başarılı")


if __name__ == "__main__":
    main()
