import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/predictions': 'http://localhost:8000',
      '/players': 'http://localhost:8000',
      '/teams': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  }
})
