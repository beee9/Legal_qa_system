import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发环境代理：/api 转发到后端 FastAPI (port 8003)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        ws: true, // WebSocket (/api/stream) 也走代理
      },
    },
  },
})
