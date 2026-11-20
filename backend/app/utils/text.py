"""Türkçe metin karşılaştırma yardımcıları."""

# Python'un lower() fonksiyonu Türkçe'yi bilmez: "İ".lower() → "i̇" (noktalı i + birleşik nokta),
# "I".lower() → "i" (Türkçe'de "ı" olmalı). Ayrıca kullanıcı "kadikoy" yazsa da
# "Kadıköy" bulunsun istiyoruz; bu yüzden Türkçe harfleri sade Latin karşılıklarına indiriyoruz.
_TR_UPPER_TO_LOWER = str.maketrans({"İ": "i", "I": "ı"})
_TR_TO_ASCII = str.maketrans({"ı": "i", "ö": "o", "ü": "u", "ş": "s", "ç": "c", "ğ": "g", "â": "a", "î": "i", "û": "u"})


def normalize_for_search(text: str) -> str:
    """'KADIKÖY', 'Kadıköy', 'kadikoy' → hepsi 'kadikoy'."""
    lowered = text.translate(_TR_UPPER_TO_LOWER).lower()
    return " ".join(lowered.translate(_TR_TO_ASCII).split())
