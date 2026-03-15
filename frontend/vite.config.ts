import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import tsconfigPaths from 'vite-tsconfig-paths'
import path from "node:path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tsconfigPaths(), tailwindcss()],
  server: {
    proxy: {
      '/v1': {
        target: 'http://localhost:5683', // 你的后端地址
        changeOrigin: true,
        // 关键：代理会把后端的 Set-Cookie 正确转发给浏览器
      }
    },
    host: '0.0.0.0', // 监听所有网卡，极其关键！
    port: 5173
  },
  resolve: {
    alias:{
      '@': path.resolve(__dirname, './src'),
    }
  }
})
