import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Geliştirmede "/api" ile başlayan istekleri FastAPI'ye yönlendir.
    // Böylece frontend kodu backend adresini bilmek zorunda kalmaz.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
