import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import OrderCard from './OrderCard'

function makeOrder(overrides = {}) {
  return {
    id: 'o1',
    status: 'PENDING',
    is_priority: false,
    note: null,
    customer_name: 'Ayşe Yılmaz',
    created_at: '2026-11-20T09:30:00Z',
    shop: { id: 's1', name: 'Cihangir Köşe', address: 'Beyoğlu' },
    allowed_next_statuses: ['ACCEPTED', 'CANCELLED'],
    items: [{ product_name: 'Cappuccino', size: 'L', milk: 'OAT', sugar: 'NONE', extra_shots: 1 }],
    ...overrides,
  }
}

describe('OrderCard (dükkân paneli)', () => {
  it('sipariş bilgilerini ve özelleştirmeleri gösterir', () => {
    render(<OrderCard order={makeOrder({ note: 'Az köpük' })} onAdvance={vi.fn()} onReject={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Cappuccino' })).toBeInTheDocument()
    expect(screen.getByText('Büyük · Yulaf süt · +1 shot')).toBeInTheDocument()
    expect(screen.getByText('“Az köpük”')).toBeInTheDocument()
    expect(screen.getByText('Ayşe Yılmaz')).toBeInTheDocument()
  })

  it('yeni siparişte "Kabul et" sonraki durumu bildirir', async () => {
    const onAdvance = vi.fn()
    const order = makeOrder()
    render(<OrderCard order={order} onAdvance={onAdvance} onReject={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: 'Kabul et' }))

    expect(onAdvance).toHaveBeenCalledWith(order, expect.objectContaining({ status: 'ACCEPTED' }))
  })

  it('hazır siparişte teslim QR ister ve reddetme düğmesi yoktur', () => {
    const order = makeOrder({ status: 'READY', allowed_next_statuses: ['COMPLETED'] })
    render(<OrderCard order={order} onAdvance={vi.fn()} onReject={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'QR okut ve teslim et' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reddet' })).not.toBeInTheDocument()
  })

  it('öncelikli (Unlimited) siparişi işaretler', () => {
    render(<OrderCard order={makeOrder({ is_priority: true })} onAdvance={vi.fn()} onReject={vi.fn()} />)

    expect(screen.getByText(/Öncelikli/)).toBeInTheDocument()
  })

  it('işlem sürerken düğmeler devre dışı', () => {
    render(<OrderCard order={makeOrder()} busy onAdvance={vi.fn()} onReject={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Kabul et' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reddet' })).toBeDisabled()
  })
})
