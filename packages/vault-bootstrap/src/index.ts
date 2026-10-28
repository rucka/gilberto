import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const PILLARS = ['me', 'pulse', 'projects', 'intelligence', 'journey', 'network'] as const

export type Pillar = (typeof PILLARS)[number]

export class UnknownPillarError extends Error {
  constructor(readonly pillar: string) {
    super(`Unknown pillar "${pillar}"; expected one of: ${PILLARS.join(', ')}`)
    this.name = 'UnknownPillarError'
  }
}

export function getSeedRoot(): string {
  return fileURLToPath(new URL('../seed', import.meta.url))
}

export function resolvePillarPath(vaultRoot: string, pillar: Pillar, _scope?: string): string {
  if (!PILLARS.includes(pillar)) throw new UnknownPillarError(pillar)
  return join(vaultRoot, pillar)
}
