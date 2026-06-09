import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  // The backend needs no CORS middleware and nothing here hardcodes a host.
  server: { proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') } } },
  test: { include: ['src/**/*.test.ts'] },
})
