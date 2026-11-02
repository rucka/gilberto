import { RootProvider } from 'fumadocs-ui/provider'
import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import './global.css'

export const metadata: Metadata = {
  title: { default: 'gilberto', template: '%s | gilberto' },
  description: 'Personal AI-native second brain: a markdown vault operated by portable skills.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body>
        <RootProvider search={{ options: { type: 'static' } }}>{children}</RootProvider>
      </body>
    </html>
  )
}
