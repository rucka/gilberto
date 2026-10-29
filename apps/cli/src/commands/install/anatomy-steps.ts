import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

export const MISSING_PACKAGE_MESSAGE =
  'vault-bootstrap content package not found; reinstall gilberto'
export const SEED_EXIT_CODE = 70

export const BUNDLED_PLUGINS = [
  { name: 'gilberto-core', description: 'core processes, mechanics and utilities' },
  { name: 'pulse-health-tracking', description: 'health tracking in the Pulse pillar' },
  { name: 'pulse-ratko', description: 'Ratko integration in the Pulse pillar' },
  { name: 'projects-venture', description: 'venture project workflows' },
  { name: 'projects-editorial', description: 'editorial project workflows' },
] as const

export const printBundledPlugins = (write: (text: string) => void): void => {
  for (const p of BUNDLED_PLUGINS) write(`${p.name} — ${p.description}\n`)
}

export type AnatomyStepsInput = {
  tmp: string
  date: string
  topics: readonly string[]
  verbose: boolean
  write: (text: string) => void
  error: (text: string) => void
  loadSeedRoot?: () => Promise<string>
}

const defaultLoadSeedRoot = async (): Promise<string> =>
  (await import('@foomakers/gilberto-vault-bootstrap')).getSeedRoot()

class SeedFailure extends Error {}

const copyTree = async (
  src: string,
  dest: string,
  transform: (path: string, text: string) => string,
  log: (kind: 'file' | 'dir', path: string) => void,
): Promise<void> => {
  await mkdir(dest, { recursive: true })
  log('dir', dest)
  for (const e of await readdir(src, { withFileTypes: true })) {
    const from = join(src, e.name)
    const to = join(dest, e.name)
    if (e.isDirectory()) {
      await copyTree(from, to, transform, log)
      continue
    }
    try {
      await writeFile(to, transform(from, await readFile(from, 'utf8')))
    } catch {
      throw new SeedFailure(`failed to seed anatomy: ${from}`)
    }
    log('file', to)
  }
}

export const runAnatomySteps = async (input: AnatomyStepsInput): Promise<number> => {
  const { tmp, date, topics, verbose, write, error } = input
  const fail = async (message: string): Promise<number> => {
    error(`${message}\n`)
    await rm(tmp, { recursive: true, force: true })
    return SEED_EXIT_CODE
  }

  let src: string
  try {
    src = join(await (input.loadSeedRoot ?? defaultLoadSeedRoot)(), 'anatomy')
    await readdir(src)
  } catch {
    return fail(MISSING_PACKAGE_MESSAGE)
  }

  const topicsPath = join(src, 'topics.md')
  const rows = [...new Set(topics)].map(t => `| ${t} | |\n`).join('')
  const transform = (path: string, text: string): string => {
    const dated = text.replaceAll('{{DATE}}', date)
    if (path !== topicsPath || rows === '') return dated
    return `${dated.endsWith('\n') ? dated : `${dated}\n`}${rows}`
  }

  try {
    await copyTree(src, join(tmp, 'anatomy'), transform, (kind, path) => {
      if (verbose) write(`wrote ${kind}=${path}\n`)
    })
  } catch (e) {
    return fail(
      e instanceof SeedFailure ? e.message : `failed to seed anatomy: ${join(tmp, 'anatomy')}`,
    )
  }
  return 0
}
