import { useQueryClient } from '@tanstack/react-query'
import { Compass, Crown, History, LayoutDashboard, LogOut } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { authApi } from '../api/endpoints'
import { useAuthStore } from '../store/authStore'
import Logo from './Logo'

const CUSTOMER_NAV = [
  { to: '/', label: 'Keşfet', icon: Compass, end: true },
  { to: '/gecmis', label: 'Siparişlerim', icon: History },
  { to: '/abonelik', label: 'Abonelik', icon: Crown },
]
const PANEL_NAV = { to: '/panel', label: 'Panel', icon: LayoutDashboard }

/** Menü role göre değişir: dükkân sahibi sadece panelini, admin hem paneli hem müşteri ekranlarını görür. */
function navFor(role) {
  if (role === 'SHOP_OWNER') return [PANEL_NAV]
  if (role === 'ADMIN') return [PANEL_NAV, ...CUSTOMER_NAV]
  return CUSTOMER_NAV
}

export default function AppLayout() {
  const user = useAuthStore((state) => state.user)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  async function handleLogout() {
    const { refreshToken, logout } = useAuthStore.getState()
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } catch {
      // Sunucuya ulaşılamasa bile cihazdaki oturum kapatılır.
    }
    logout()
    queryClient.clear() // önceki kullanıcının verileri ekranda kalmasın
    navigate('/giris', { replace: true })
  }

  const navItems = navFor(user?.role)
  const initials = (user?.full_name ?? 'K').trim().charAt(0).toLocaleUpperCase('tr-TR')

  return (
    <>
      <a href="#icerik" className="skip-link">İçeriğe geç</a>
      <header className="app-header">
        <div className="app-header__inner">
          <Logo />
          <nav className="top-nav" aria-label="Ana menü">
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end}>
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="user-chip">
            <span className="user-chip__avatar" aria-hidden>
              {initials}
            </span>
            <span className="user-chip__name">{user?.full_name ?? 'Misafir'}</span>
            <button type="button" className="icon-btn" onClick={handleLogout} title="Çıkış yap" aria-label="Çıkış yap">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </header>

      <main id="icerik" tabIndex={-1}>
        <Outlet />
      </main>

      <nav className="bottom-nav" aria-label="Alt menü" style={{ gridTemplateColumns: `repeat(${navItems.length}, 1fr)` }}>
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}>
            <Icon size={22} />
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}
