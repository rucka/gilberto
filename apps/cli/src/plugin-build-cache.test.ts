import { execFileSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = join(dirname(fileURLToPath(import.meta.url)), '../../..')
const run = (cmd: string, args: string[]) =>
  execFileSync(cmd, args, { cwd: root, encoding: 'utf8', stdio: 'pipe', timeout: 60_000 })

describe('generated apps/cli/plugins (r1-5)', () => {
  it('is gitignored', () => {
    expect(() =>
      run('git', ['check-ignore', '-q', 'apps/cli/plugins/gilberto-core/.claude-plugin/plugin.json']),
    ).not.toThrow()
  })

  it('is a cached build output keyed on root plugins/', () => {
    const dry = JSON.parse(
      run('pnpm', ['exec', 'turbo', 'run', 'build', '--filter=gilberto', '--dry=json']),
    ) as { tasks: { taskId: string; outputs: string[]; inputs: Record<string, string> }[] }
    const task = dry.tasks.find(t => t.taskId === 'gilberto#build')!
    expect(task.outputs).toContain('plugins/**')
    expect(Object.keys(task.inputs)).toContain('../../plugins/gilberto-core/.claude-plugin/plugin.json')
  }, 60_000)
})
