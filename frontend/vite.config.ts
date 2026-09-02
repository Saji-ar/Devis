import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En dev, l'API tourne sur :8000 et on proxifie /api pour eviter les soucis de CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
