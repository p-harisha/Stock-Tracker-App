import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

// Builds the favicon, Apple touch icon and manifest icons from one SVG.
// Maskable and Apple icons get padding, so fill it with the icon's blue instead of white.
const padded = { resizeOptions: { background: '#1d5c8a' } }

export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    ...minimal2023Preset,
    maskable: { ...minimal2023Preset.maskable, ...padded },
    apple: { ...minimal2023Preset.apple, ...padded },
  },
  images: ['public/favicon.svg'],
})
