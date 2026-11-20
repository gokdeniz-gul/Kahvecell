import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DEFAULT_FILTERS, filtersToParams } from '../lib/shopFilters'
import ShopFilters from './ShopFilters'

describe('filtersToParams', () => {
  it('varsayılanda sadece sıralama gönderilir', () => {
    expect(filtersToParams(DEFAULT_FILTERS)).toEqual({ sort: 'distance' })
  })

  it('seçilen filtreleri backend parametrelerine çevirir', () => {
    expect(filtersToParams({ openNow: true, radiusKm: '3', minRating: '4.5', sort: 'rating' })).toEqual({
      open_now: true,
      radius_km: 3,
      min_rating: 4.5,
      sort: 'rating',
    })
  })
})

describe('ShopFilters (case 3.3)', () => {
  it('mesafe seçimi filtreyi günceller', async () => {
    const onChange = vi.fn()
    render(<ShopFilters filters={DEFAULT_FILTERS} onChange={onChange} />)

    await userEvent.selectOptions(screen.getByLabelText('Mesafe'), '1')

    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, radiusKm: '1' })
  })

  it('puan seçimi ve "şu an açık" filtreyi günceller', async () => {
    const onChange = vi.fn()
    render(<ShopFilters filters={DEFAULT_FILTERS} onChange={onChange} />)

    await userEvent.selectOptions(screen.getByLabelText('Puan'), '4.5')
    await userEvent.click(screen.getByRole('button', { name: /Şu an açık/ }))

    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, minRating: '4.5' })
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS, openNow: true })
  })

  it('filtre varken "temizle" varsayılana döndürür', async () => {
    const onChange = vi.fn()
    render(<ShopFilters filters={{ ...DEFAULT_FILTERS, radiusKm: '3' }} onChange={onChange} />)

    await userEvent.click(screen.getByRole('button', { name: 'Filtreleri temizle' }))

    expect(onChange).toHaveBeenCalledWith(DEFAULT_FILTERS)
  })

  it('filtre yokken "temizle" görünmez', () => {
    render(<ShopFilters filters={DEFAULT_FILTERS} onChange={vi.fn()} />)

    expect(screen.queryByRole('button', { name: 'Filtreleri temizle' })).not.toBeInTheDocument()
  })
})
