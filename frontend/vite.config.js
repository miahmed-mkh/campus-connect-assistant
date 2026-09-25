import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Redirige les appels /api vers le backend FastAPI en local
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
