/** Form doğrulama yardımcıları (client-side). Sunucu da aynı kuralları ayrıca uygular. */

/** "4242424242424242" → "4242 4242 4242 4242" */
export const formatCardNumber = (value) =>
  value.replace(/\D/g, '').slice(0, 16).replace(/(\d{4})(?=\d)/g, '$1 ')

/** "1230" → "12/30" */
export const formatExpiry = (value) =>
  value.replace(/\D/g, '').slice(0, 4).replace(/^(\d{2})(\d)/, '$1/$2')

/**
 * Kart formu doğrulaması. Hatalı alanları { alan: mesaj } olarak döner; boşsa form geçerli.
 * `now` testlerde sabit bir tarih verebilmek için parametre.
 */
export function validateCard(card, now = new Date()) {
  const errors = {}
  if (card.holder.trim().length < 2) errors.holder = 'Kart üzerindeki ismi gir.'
  if (card.number.replace(/\s/g, '').length !== 16) errors.number = 'Kart numarası 16 haneli olmalı.'

  const match = card.expiry.match(/^(\d{2})\/(\d{2})$/)
  if (!match || Number(match[1]) < 1 || Number(match[1]) > 12) {
    errors.expiry = 'AA/YY biçiminde gir.'
  } else {
    const [month, year] = [Number(match[1]), 2000 + Number(match[2])]
    if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) {
      errors.expiry = 'Kartın süresi dolmuş.'
    }
  }

  if (!/^\d{3,4}$/.test(card.cvc)) errors.cvc = '3 haneli güvenlik kodu.'
  return errors
}
