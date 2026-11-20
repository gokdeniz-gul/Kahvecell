/**
 * Backend endpoint'leri. Bileşenler URL bilmez; sadece bu fonksiyonları çağırır.
 * Her fonksiyon backend cevabındaki "data" alanını döner (client.js zarfı açıyor).
 */
import { api } from './client'

export const authApi = {
  register: (phone) => api.post('/auth/register', { phone_number: phone }),
  login: (phone) => api.post('/auth/login', { phone_number: phone }),
  verifyOtp: (phone, code) => api.post('/auth/verify-otp', { phone_number: phone, code }),
  logout: (refreshToken) => api.post('/auth/logout', { refresh_token: refreshToken }),
  me: () => api.get('/users/me'),
  updateMe: (changes) => api.patch('/users/me', changes),
}

export const shopsApi = {
  list: (params) => api.get('/shops', { params }),
  get: (shopId, params) => api.get(`/shops/${shopId}`, { params }),
  menu: (shopId) => api.get(`/shops/${shopId}/menu`),
}

export const subscriptionsApi = {
  plans: () => api.get('/subscriptions/plans'),
  mine: () => api.get('/subscriptions/me'),
  start: (planType, transactionId) =>
    api.post('/subscriptions', { plan_type: planType, transaction_id: transactionId }),
  changePlan: (planType, transactionId = null) =>
    api.patch('/subscriptions/me', { plan_type: planType, transaction_id: transactionId }),
  cancel: () => api.delete('/subscriptions/me'),
}

export const paymentsApi = {
  process: (planType, card) => api.post('/payments/process', { plan_type: planType, card }),
  history: () => api.get('/payments/me'),
}

export const ordersApi = {
  create: (order) => api.post('/orders', order),
  get: (orderId) => api.get(`/orders/${orderId}`),
  history: (params) => api.get('/orders/history', { params }),
  reorder: (orderId) => api.post(`/orders/${orderId}/reorder`),
  cancel: (orderId) => api.patch(`/orders/${orderId}/status`, { status: 'CANCELLED' }),
}

/** React Query anahtarları tek yerde: hangi veri hangi isimle önbellekte, karışmasın. */
export const queryKeys = {
  shops: (params) => ['shops', params],
  shop: (shopId, params) => ['shop', shopId, params],
  menu: (shopId) => ['menu', shopId],
  plans: ['plans'],
  subscription: ['subscription'],
  payments: ['payments'],
  orders: ['orders'],
  order: (orderId) => ['orders', orderId],
}
