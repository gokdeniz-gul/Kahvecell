import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '../store/authStore'
import { CustomerArea, GuestOnly, RequireAuth, RequireRole } from './RouteGuards'

function renderAt(path, user) {
  if (user) useAuthStore.setState({ accessToken: 'token', refreshToken: 'r', user })
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<GuestOnly />}>
          <Route path="/giris" element={<p>Giriş ekranı</p>} />
        </Route>
        <Route element={<RequireAuth />}>
          <Route element={<CustomerArea />}>
            <Route path="/" element={<p>Keşfet</p>} />
          </Route>
          <Route element={<RequireRole roles={['SHOP_OWNER', 'ADMIN']} />}>
            <Route path="/panel" element={<p>Dükkân paneli</p>} />
          </Route>
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

const customer = { full_name: 'Ayşe', role: 'CUSTOMER' }
const owner = { full_name: 'Mehmet', role: 'SHOP_OWNER' }

afterEach(() => useAuthStore.getState().logout())

describe('sayfa korumaları', () => {
  it('giriş yapmamış kullanıcı giriş ekranına gider', () => {
    renderAt('/')
    expect(screen.getByText('Giriş ekranı')).toBeInTheDocument()
  })

  it('müşteri keşfet ekranını görür', () => {
    renderAt('/', customer)
    expect(screen.getByText('Keşfet')).toBeInTheDocument()
  })

  it('dükkân sahibi müşteri ekranı yerine paneline yönlendirilir', () => {
    renderAt('/', owner)
    expect(screen.getByText('Dükkân paneli')).toBeInTheDocument()
  })

  it('müşteri dükkân paneline giremez', () => {
    renderAt('/panel', customer)
    expect(screen.getByText('Keşfet')).toBeInTheDocument()
  })

  it('giriş yapmış kullanıcı giriş ekranını görmez', () => {
    renderAt('/giris', customer)
    expect(screen.getByText('Keşfet')).toBeInTheDocument()
  })

  it('profilini tamamlamamış kullanıcı kayıt akışında kalır', () => {
    renderAt('/giris', { full_name: null, role: 'CUSTOMER' })
    expect(screen.getByText('Giriş ekranı')).toBeInTheDocument()
  })
})
