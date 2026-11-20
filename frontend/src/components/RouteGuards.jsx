import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore, useIsLoggedIn } from '../store/authStore'

/** Giriş yapmamış kullanıcıyı giriş ekranına yollar; girişten sonra kaldığı sayfaya döner. */
export function RequireAuth() {
  const isLoggedIn = useIsLoggedIn()
  const location = useLocation()
  if (!isLoggedIn) return <Navigate to="/giris" replace state={{ from: location.pathname }} />
  return <Outlet />
}

/** Sadece belirli rollerin girebileceği sayfalar (örn. dükkân paneli). */
export function RequireRole({ roles }) {
  const role = useAuthStore((state) => state.user?.role)
  return roles.includes(role) ? <Outlet /> : <Navigate to="/" replace />
}

/** Müşteri ekranları: dükkân sahibi buralara gelirse kendi paneline yönlendirilir. */
export function CustomerArea() {
  const role = useAuthStore((state) => state.user?.role)
  return role === 'SHOP_OWNER' ? <Navigate to="/panel" replace /> : <Outlet />
}

/**
 * Giriş yapmış kullanıcı giriş/kayıt ekranını görmesin.
 * İstisna: kodu doğrulamış ama profilini henüz tamamlamamış kullanıcı (kayıt akışının 3. adımı).
 */
export function GuestOnly() {
  const isLoggedIn = useIsLoggedIn()
  const hasProfile = useAuthStore((state) => Boolean(state.user?.full_name))
  return isLoggedIn && hasProfile ? <Navigate to="/" replace /> : <Outlet />
}
