import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// The dev server forwards /api to the FastAPI backend on port 8000.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // Icons and their <link> tags come from pwa-assets.config.ts.
      pwaAssets: { config: true },
      manifest: {
        name: 'Sector Watchlist',
        short_name: 'Watchlist',
        description: 'Track NSE and BSE tickers by sector with Buy / Hold / Sell signals.',
        theme_color: '#1d5c8a',
        background_color: '#f3f5f7',
        display: 'standalone',
        start_url: '/',
      },
      workbox: {
        // /api pages (like the Kite login redirect) must reach the backend, not the app shell.
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // Show the last fetched data when offline; always try the network first.
            urlPattern: /\/api\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'api', networkTimeoutSeconds: 10, expiration: { maxEntries: 50 } },
          },
          {
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\//,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'google-fonts', expiration: { maxEntries: 20 } },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
})
