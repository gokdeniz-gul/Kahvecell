import { describe, expect, it } from 'vitest'

import { formatCardNumber, formatExpiry, validateCard } from './validation'

const NOW = new Date(2026, 10, 20) // 20 Kasım 2026
const validCard = { holder: 'AYSE YILMAZ', number: '4242 4242 4242 4242', expiry: '12/30', cvc: '123' }

describe('validateCard', () => {
  it('geçerli kartta hata yok', () => {
    expect(validateCard(validCard, NOW)).toEqual({})
  })

  it('her alanın hatasını ayrı ayrı bildirir', () => {
    const errors = validateCard({ holder: 'A', number: '4242', expiry: '13/30', cvc: '1' }, NOW)
    expect(Object.keys(errors).sort()).toEqual(['cvc', 'expiry', 'holder', 'number'])
  })

  it('süresi geçmiş kartı reddeder', () => {
    expect(validateCard({ ...validCard, expiry: '10/26' }, NOW).expiry).toBe('Kartın süresi dolmuş.')
  })

  it('bu ay biten kartı kabul eder', () => {
    expect(validateCard({ ...validCard, expiry: '11/26' }, NOW)).toEqual({})
  })
})

describe('kart formu biçimlendirme', () => {
  it('kart numarasını 4lü gruplar ve 16 haneyle sınırlar', () => {
    expect(formatCardNumber('42424242424242429999')).toBe('4242 4242 4242 4242')
  })

  it('son kullanma tarihine / ekler', () => {
    expect(formatExpiry('1230')).toBe('12/30')
    expect(formatExpiry('1a2')).toBe('12')
  })
})
