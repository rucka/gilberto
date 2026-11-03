import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { registryPath } from './registry.js'

const SEED = `---
type: anatomy-plugins
---

# Plugins

| Plugin | Version | Installed |
| ------ | ------- | --------- |
`

export const SEED_PLUGINS = SEED

export function makeVault(content = SEED): string {
  const vault = mkdtempSync(join(tmpdir(), 'vault-'))
  mkdirSync(join(vault, 'anatomy'))
  writeFileSync(registryPath(vault), content)
  return vault
}

export function write(root: string, rel: string, content: string): void {
  mkdirSync(dirname(join(root, rel)), { recursive: true })
  writeFileSync(join(root, rel), content)
}

export function makePlugin(
  manifest: Record<string, unknown>,
  files: Record<string, string> = {},
  parent = mkdtempSync(join(tmpdir(), 'plug-')),
  dir = '.',
): string {
  const root = join(parent, dir)
  write(root, join('.claude-plugin', 'plugin.json'), JSON.stringify(manifest))
  for (const [rel, c] of Object.entries(files)) write(root, rel, c)
  return root
}

export const pillarManifest = (name: string, extra: Record<string, unknown> = {}) => ({
  name,
  description: 'd',
  version: '1.2.3',
  gilberto: {
    kind: 'pillar',
    pillar: 'pulse',
    playbooks: { 'pulse/daily': './playbooks/daily.md' },
    templates: ['./templates/habit'],
    ...extra,
  },
})

export const pillarFiles = {
  'playbooks/daily.md': 'PLAYBOOK',
  'templates/habit/a.md': 'A',
  'templates/habit/sub/b.md': 'B',
}

export function gitRepo(root: string): string {
  const git = (...a: string[]): void => {
    execFileSync('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', ...a], {
      cwd: root,
      stdio: 'pipe',
    })
  }
  git('init', '-q')
  git('add', '-A')
  git('commit', '-q', '-m', 'init')
  return `file://${root}`
}
