import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendHost = process.env.VITE_BACKEND_HOST ?? 'localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: `http://${backendHost}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://${backendHost}`,
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
