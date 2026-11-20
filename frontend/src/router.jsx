import { createBrowserRouter } from 'react-router-dom'

import AppLayout from './components/AppLayout'
import { CustomerArea, GuestOnly, RequireAuth, RequireRole } from './components/RouteGuards'
import { Loading } from './components/StateViews'
import { STAFF_ROLES } from './lib/format'
import AuthPage from './pages/AuthPage'

/**
 * Sayfalar "lazy" yüklenir: her sayfanın kodu ayrı bir dosyaya bölünür ve sadece o sayfaya
 * gidilince indirilir. Örneğin harita kütüphanesi giriş ekranında hiç yüklenmez (case 8.1 performans).
 */
const page = (load) => async () => ({ Component: (await load()).default })

/**
 * Sayfa haritası:
 *   /giris, /kayit                → herkese açık (giriş ekranı ilk açılan sayfa olduğu için lazy değil)
 *   /, /dukkan/:id, /siparis/...  → müşteri
 *   /panel                        → dükkân sahibi / admin
 */
export const router = createBrowserRouter([
  {
    element: <GuestOnly />,
    children: [
      // key: giriş ↔ kayıt arasında geçince form sıfırdan başlasın
      { path: '/giris', element: <AuthPage key="login" mode="login" /> },
      { path: '/kayit', element: <AuthPage key="register" mode="register" /> },
    ],
  },
  {
    element: <RequireAuth />,
    HydrateFallback: Loading,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            // Dükkân sahibi müşteri ekranlarına girerse kendi paneline yönlendirilir.
            element: <CustomerArea />,
            children: [
              { path: '/', lazy: page(() => import('./pages/HomePage')) },
              { path: '/dukkan/:shopId', lazy: page(() => import('./pages/ShopDetailPage')) },
              { path: '/dukkan/:shopId/siparis/:productId', lazy: page(() => import('./pages/OrderPage')) },
              { path: '/siparis/:orderId', lazy: page(() => import('./pages/OrderQrPage')) },
              { path: '/gecmis', lazy: page(() => import('./pages/HistoryPage')) },
              { path: '/abonelik', lazy: page(() => import('./pages/SubscriptionPage')) },
            ],
          },
          {
            element: <RequireRole roles={STAFF_ROLES} />,
            children: [{ path: '/panel', lazy: page(() => import('./pages/OwnerPanelPage')) }],
          },
          { path: '*', lazy: page(() => import('./pages/NotFoundPage')) },
        ],
      },
    ],
  },
])
