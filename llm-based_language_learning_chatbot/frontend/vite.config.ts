import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueJsx(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
 server: {
  proxy: {
    // 将 '/api' 修改为 '/sessions'，因为这是你报错里出现的路径
    '/sessions': {
      target: 'http://127.0.0.1:8000', // 建议改用 127.0.0.1 避开 IPv6 锁定
      changeOrigin: true,
      // 如果后端接口本身没有 /api，这里就不用 rewrite
    },
    '/ws': {
      target: 'ws://127.0.0.1:8000',
      ws: true,
      changeOrigin: true
    }
  }
}
})
