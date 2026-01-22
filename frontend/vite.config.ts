import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/v1': {
        target: 'http://localhost:5683', // 你的后端地址
        changeOrigin: true,
        // 关键：代理会把后端的 Set-Cookie 正确转发给浏览器
      }
    }
  },
  resolve: {
    alias:{
      '@': path.resolve(__dirname, './src'),
    }
  }
})
