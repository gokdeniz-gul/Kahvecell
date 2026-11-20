import { describe, expect, it } from 'vitest'

import { MILKS, formatDistance, formatTL, labelOf, normalizePhone } from './format'

describe('normalizePhone', () => {
  it.each(['5321234567', '05321234567', '+905321234567', '+90 532 123 45 67', '0532-123-45-67'])(
    '%s → 5321234567',
    (input) => expect(normalizePhone(input)).toBe('5321234567'),
  )

  it.each(['123', '4321234567', '532123456', 'abc', ''])('%s geçersiz', (input) => {
    expect(normalizePhone(input)).toBeNull()
  })
})

describe('formatTL', () => {
  it('kuruşu Türk lirasına çevirir', () => {
    expect(formatTL(8999)).toMatch(/89,99/)
    expect(formatTL(8999)).toMatch(/₺|TL/)
  })
})

describe('formatDistance', () => {
  it('1 km altını metre olarak gösterir', () => expect(formatDistance(0.6)).toBe('600 m'))
  it('1 km ve üstünü tek ondalıkla gösterir', () => expect(formatDistance(6.62)).toBe('6.6 km'))
})

describe('labelOf', () => {
  it('değerin Türkçe etiketini bulur', () => expect(labelOf(MILKS, 'OAT')).toBe('Yulaf'))
  it('bilinmeyen değeri olduğu gibi döner', () => expect(labelOf(MILKS, 'SOY')).toBe('SOY'))
})
