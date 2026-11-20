import axios from 'axios'

import { useAuthStore } from '../store/authStore'

// .env'de boş bırakılırsa ("") da varsayılana düşsün diye ?? değil || kullanıyoruz.
export const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

/** Backend'in { success:false, error:{ code, message, details } } cevabını taşıyan hata. */
export class ApiError extends Error {
  constructor({ message, code, status, details }) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

function toApiError(error) {
  const body = error.response?.data?.error
  if (body) {
    return new ApiError({ ...body, status: error.response.status })
  }
  return new ApiError({
    message: error.response
      ? 'Sunucuda beklenmeyen bir hata oluştu.'
      : 'Sunucuya ulaşılamıyor. Backend açık mı?',
    code: error.response ? 'UNKNOWN' : 'NETWORK_ERROR',
    status: error.response?.status ?? 0,
  })
}

export const api = axios.create({ baseURL: BASE_URL, timeout: 15000 })

// Her isteğe giriş token'ını ekle.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Access token'ın süresi dolunca refresh token ile sessizce yenisini al.
// Aynı anda birden çok istek 401 alırsa tek bir yenileme yapılır (hepsi onu bekler).
let refreshPromise = null

function refreshAccessToken() {
  const { refreshToken, setTokens, logout } = useAuthStore.getState()
  if (!refreshToken) return Promise.reject(new Error('Refresh token yok'))

  refreshPromise ??= axios
    .post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
    .then(({ data }) => {
      setTokens(data.data.access_token, data.data.refresh_token)
      return data.data.access_token
    })
    .catch((error) => {
      logout() // Yenilenemedi: oturum gerçekten bitti, giriş ekranına dönülür.
      throw error
    })
    .finally(() => {
      refreshPromise = null
    })
  return refreshPromise
}

api.interceptors.response.use(
  // Başarılı cevaplarda zarfı aç: bileşenler doğrudan "data"yı alsın.
  (response) => response.data.data,
  async (error) => {
    const original = error.config
    const code = error.response?.data?.error?.code

    if (error.response?.status === 401 && code === 'TOKEN_EXPIRED' && !original._retried) {
      original._retried = true
      try {
        const token = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      } catch {
        throw toApiError(error)
      }
    }
    if (error.response?.status === 401 && code === 'TOKEN_INVALID') {
      useAuthStore.getState().logout()
    }
    throw toApiError(error)
  },
)
