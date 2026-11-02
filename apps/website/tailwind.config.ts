import type { Config } from 'tailwindcss'
import { createPreset } from 'fumadocs-ui/tailwind-plugin'

// Neutral fumadocs theme; brand tokens land with epic #29.
export default {
  content: ['./app/**/*.{ts,tsx}', './content/**/*.mdx', './node_modules/fumadocs-ui/dist/**/*.js'],
  darkMode: 'class',
  presets: [createPreset()],
} satisfies Config
