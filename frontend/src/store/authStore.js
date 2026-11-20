import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

/**
 * Giriş durumu (client state). Sayfa yenilense de kaybolmasın diye localStorage'da tutulur.
 * Sunucudan gelen veriler (dükkânlar, siparişler...) burada DEĞİL, React Query'de tutulur.
 */
export const useAuthStore = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setSession: ({ accessToken, refreshToken, user }) => set({ accessToken, refreshToken, user }),
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: 'kahvecell-auth',
      storage: createJSONStorage(() => localStorage),
    },
  ),
)

export const useIsLoggedIn = () => useAuthStore((state) => Boolean(state.accessToken))
