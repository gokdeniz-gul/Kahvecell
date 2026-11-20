import { createBrowserRouter } from 'react-router-dom'

import AppLayout from './components/AppLayout'
import { GuestOnly, RequireAuth } from './components/RouteGuards'
import AuthPage from './pages/AuthPage'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import NotFoundPage from './pages/NotFoundPage'
import OrderPage from './pages/OrderPage'
import OrderQrPage from './pages/OrderQrPage'
import ShopDetailPage from './pages/ShopDetailPage'
import SubscriptionPage from './pages/SubscriptionPage'

/**
 * Sayfa haritası:
 *   /giris, /kayit                      → herkese açık
 *   / (keşfet), /dukkan/:id, ...        → giriş gerektirir (AppLayout: üst menü + alt menü)
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
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/', element: <HomePage /> },
          { path: '/dukkan/:shopId', element: <ShopDetailPage /> },
          { path: '/dukkan/:shopId/siparis/:productId', element: <OrderPage /> },
          { path: '/siparis/:orderId', element: <OrderQrPage /> },
          { path: '/gecmis', element: <HistoryPage /> },
          { path: '/abonelik', element: <SubscriptionPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
])
