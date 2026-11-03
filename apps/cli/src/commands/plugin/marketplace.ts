import { readFileSync } from 'node:fs'
import { join } from 'node:path'

export function marketplaceHas(name: string, env: NodeJS.ProcessEnv): boolean {
  const home = env['HOME']
  if (!home) return false
  try {
    const data = JSON.parse(
      readFileSync(join(home, '.claude', 'plugins', 'installed_plugins.json'), 'utf8'),
    ) as { plugins?: Record<string, unknown> }
    return Object.keys(data.plugins ?? {}).some(k => k.startsWith(`${name}@`))
  } catch {
    return false
  }
}
