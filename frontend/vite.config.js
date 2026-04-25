import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // WebSocket endpoints
      '/ws': {
        target: BACKEND,
        ws: true,
        changeOrigin: true,
      },
      // API paths that overlap with frontend routes
      '/patient/psychoeducation-chat': {
        target: BACKEND,
        changeOrigin: true,
      },
      '/therapist/ai-chat': {
        target: BACKEND,
        changeOrigin: true,
      },
      // General backend API paths (http + websocket)
      '^/(auth|patients|emergency-personnel|resources|sessions|homeworks|fear-ladders|erp|chat|voice|imaginal-generator|education|api|health|media|signup)': {
        target: BACKEND,
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
})
