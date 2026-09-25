import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'API_PROXY_TARGET')

  // Mantener la conexión local actual si no se configura otra dirección.
  const apiProxyTarget =
    env.API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],

    server: {
      port: 5173,
      host: '0.0.0.0',

      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})