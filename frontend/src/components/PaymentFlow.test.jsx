import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { paymentsApi, subscriptionsApi } from '../api/endpoints'
import PaymentFlow from './PaymentFlow'

vi.mock('../api/endpoints', () => ({
  paymentsApi: { process: vi.fn() },
  subscriptionsApi: { start: vi.fn(), changePlan: vi.fn() },
}))

const starter = { plan_type: 'STARTER', name: 'Starter', monthly_price_kurus: 8999 }
const checkout = { plan: starter, mode: 'start', amount: 8999 }

function renderFlow(props = {}) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const handlers = { onPaid: vi.fn(), onClose: vi.fn() }
  render(
    <QueryClientProvider client={client}>
      <PaymentFlow checkout={checkout} {...handlers} {...props} />
    </QueryClientProvider>,
  )
  return handlers
}

async function fillCard(number = '4242424242424242') {
  await userEvent.type(screen.getByLabelText('Kart üzerindeki isim'), 'AYSE YILMAZ')
  await userEvent.type(screen.getByLabelText('Kart numarası'), number)
  await userEvent.type(screen.getByLabelText('Son kullanma'), '1230')
  await userEvent.type(screen.getByLabelText('CVC'), '123')
  await userEvent.click(screen.getByRole('button', { name: 'Devam et' }))
}

afterEach(() => vi.clearAllMocks())

describe('PaymentFlow (case 12.2: kart formu → onay → sonuç)', () => {
  it('geçersiz kartta onay adımına geçmez', async () => {
    renderFlow()

    await userEvent.click(screen.getByRole('button', { name: 'Devam et' }))

    expect(screen.getByText('Kart numarası 16 haneli olmalı.')).toBeInTheDocument()
    expect(screen.queryByText('Ödenecek tutar')).not.toBeInTheDocument()
  })

  it('onay ekranı özeti gösterir, ödeme başarılıysa sonuç ekranına geçer', async () => {
    paymentsApi.process.mockResolvedValue({ transaction_id: 'TXN-ABC123' })
    subscriptionsApi.start.mockResolvedValue({})
    const { onPaid, onClose } = renderFlow()

    await fillCard()

    // Onay ekranı: henüz ödeme yapılmadı
    expect(screen.getByText('Ödenecek tutar')).toBeInTheDocument()
    expect(screen.getByText(/•••• 4242/)).toBeInTheDocument()
    expect(paymentsApi.process).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: /Onayla ve/ }))

    expect(await screen.findByText('Ödeme başarılı')).toBeInTheDocument()
    expect(screen.getByText('TXN-ABC123')).toBeInTheDocument()
    expect(paymentsApi.process).toHaveBeenCalledWith('STARTER', expect.objectContaining({
      card_number: '4242 4242 4242 4242', expiry_month: 12, expiry_year: 2030,
    }))
    expect(subscriptionsApi.start).toHaveBeenCalledWith('STARTER', 'TXN-ABC123')
    expect(onPaid).toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Tamam' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('reddedilen kartta sonuç ekranı ve "başka kartla dene"', async () => {
    const declined = Object.assign(new Error('Ödeme reddedildi. Lütfen başka bir kart deneyin.'), {
      code: 'PAYMENT_DECLINED',
      details: { transaction_id: 'TXN-FAIL01' },
    })
    paymentsApi.process.mockRejectedValue(declined)
    renderFlow()

    await fillCard('4000000000000002')
    await userEvent.click(screen.getByRole('button', { name: /Onayla ve/ }))

    expect(await screen.findByText('Ödeme reddedildi')).toBeInTheDocument()
    expect(screen.getByText('TXN-FAIL01')).toBeInTheDocument()
    expect(subscriptionsApi.start).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Başka kartla dene' }))
    expect(screen.getByLabelText('Kart numarası')).toHaveValue('')
  })

  it('yükseltmede fark ödenir ve paket değiştirilir', async () => {
    paymentsApi.process.mockResolvedValue({ transaction_id: 'TXN-UP' })
    subscriptionsApi.changePlan.mockResolvedValue({})
    renderFlow({ checkout: { plan: { ...starter, plan_type: 'PREMIUM', name: 'Premium' }, mode: 'upgrade', amount: 6000 } })

    await fillCard()
    expect(screen.getByText('Paket yükseltme (fiyat farkı)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Onayla ve/ }))

    expect(await screen.findByText('Ödeme başarılı')).toBeInTheDocument()
    expect(subscriptionsApi.changePlan).toHaveBeenCalledWith('PREMIUM', 'TXN-UP')
  })
})
