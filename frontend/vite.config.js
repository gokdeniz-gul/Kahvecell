import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Geliştirmede "/api" ile başlayan istekleri FastAPI'ye yönlendir.
    // Böylece frontend kodu backend adresini bilmek zorunda kalmaz.
    // Hedef değiştirilebilir (örn. Docker'da: VITE_PROXY_TARGET=http://backend:8000).
    proxy: {
      '/api': process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
    },
  },
  // Vitest: tarayıcı benzeri ortamda (jsdom) bileşen ve fonksiyon testleri
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
})
