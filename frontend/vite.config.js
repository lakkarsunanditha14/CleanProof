import fs from 'node:fs'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// A self-signed certificate in ./certs turns on HTTPS, which phone browsers require for the
// camera and GPS. The phone reaches the app over Wi-Fi; API and photo requests are passed on
// to the backend on this laptop, so the backend itself stays private.
const https = fs.existsSync('certs/key.pem')
  ? { key: fs.readFileSync('certs/key.pem'), cert: fs.readFileSync('certs/cert.pem') }
  : undefined

const backend = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    host: true, // also listen on the Wi-Fi network, not only this laptop
    port: 5173,
    https,
    // Allow visitors through a Cloudflare quick tunnel (public https link for phones, any network)
    allowedHosts: ['.trycloudflare.com'],
    proxy: {
      '/api': backend,
      '/static': backend,
    },
  },
})
