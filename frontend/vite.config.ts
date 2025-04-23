import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api/markets': {
        target: 'http://leaderboard:8003',
        changeOrigin: true,
        rewrite: (path) => path,
      },
      '/api/leaderboard': {
        target: 'http://leaderboard:8003',
        changeOrigin: true,
        rewrite: (path) => path,
      },
      '/api/alerts': {
        target: 'http://alerts:8004',
        changeOrigin: true,
        rewrite: (path) => path,
      },
      '/api/v1/rationality': {
        target: 'http://rationality:8005',
        changeOrigin: true,
        rewrite: (path) => path,
      },
      '/ws': {
        target: 'ws://aggregator:8002',
        ws: true,
      },
    },
  },
}) 