import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '../api/endpoints'
import { useAuthStore } from '../store/authStore'
import ProfilePage from './ProfilePage'

vi.mock('../api/endpoints', () => ({ authApi: { updateMe: vi.fn() } }))

function renderPage() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ProfilePage />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  useAuthStore.setState({
    accessToken: 't',
    user: {
      phone_number: '5551234567',
      full_name: 'Ayşe Yılmaz',
      email: null,
      preferences: { coffee_types: ['LATTE'], allergens: [] },
    },
  })
})

afterEach(() => {
  vi.clearAllMocks()
  useAuthStore.getState().logout()
})

describe('ProfilePage (case 3.1)', () => {
  it('mevcut tercihleri seçili gösterir', () => {
    renderPage()

    expect(screen.getByRole('button', { name: 'Latte' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Laktoz' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('tercih ve alerjenleri kaydeder, store güncellenir', async () => {
    const saved = { phone_number: '5551234567', full_name: 'Ayşe Yılmaz', email: null,
      preferences: { coffee_types: ['LATTE', 'TURKISH'], allergens: ['LACTOSE'] } }
    authApi.updateMe.mockResolvedValue(saved)
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: 'Türk kahvesi' }))
    await userEvent.click(screen.getByRole('button', { name: 'Laktoz' }))
    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }))

    expect(authApi.updateMe).toHaveBeenCalledWith({
      full_name: 'Ayşe Yılmaz',
      email: null,
      preferences: { coffee_types: ['LATTE', 'TURKISH'], allergens: ['LACTOSE'] },
    })
    expect(await screen.findByText('Profilin kaydedildi.')).toBeInTheDocument()
    expect(useAuthStore.getState().user.preferences.allergens).toEqual(['LACTOSE'])
  })

  it('geçersiz e-postayı göndermeden önce yakalar', async () => {
    renderPage()

    await userEvent.type(screen.getByLabelText(/E-posta/), 'bozuk')
    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }))

    expect(screen.getByText('Geçerli bir e-posta gir.')).toBeInTheDocument()
    expect(authApi.updateMe).not.toHaveBeenCalled()
  })
})
