import { spawnSync } from 'node:child_process'
import { mkdir, readFile, realpath, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { makeCtx, tmpRoot } from '../test-utils/index.js'
import { hooksStep } from './07-hooks.js'

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))
const read = (p: string) => readFile(p, 'utf8').catch(() => '')
const waitFor = async (p: string, ms = 4000): Promise<string> => {
  for (let t = 0; t < ms; t += 50) {
    const c = await read(p)
    if (c !== '') return c
    await sleep(50)
  }
  return ''
}

const EVENTS = ['SessionStart', 'PreCompact', 'SessionEnd'] as const
type Ev = (typeof EVENTS)[number]
const SKILLS: Record<Ev, string> = {
  SessionStart: 'gilberto-process-next',
  PreCompact: 'gilberto-process-capture',
  SessionEnd: 'gilberto-process-reflect',
}
const FILES: Record<Ev, string> = {
  SessionStart: 'gilberto.session-start.sh',
  PreCompact: 'gilberto.pre-compact.sh',
  SessionEnd: 'gilberto.session-end.sh',
}
const META = ['a"b', 'a\\b']
const cases = EVENTS.flatMap(ev => META.map(n => [ev, n] as const))
const HOSTILE = ['v$(echo INJECTED 1>&2)', 'w`echo INJECTED 1>&2`']

const install = async (name: string, skills: string[] = []) => {
  const base = await tmpRoot()
  const root = join(base, name)
  await mkdir(root, { recursive: true })
  for (const s of skills) {
    await mkdir(join(root, '.claude/skills', s), { recursive: true })
    await writeFile(join(root, '.claude/skills', s, 'SKILL.md'), '# stub\n')
  }
  await hooksStep({ targetPath: root }, makeCtx().ctx)
  const settings = JSON.parse(await readFile(join(root, '.claude/settings.json'), 'utf8')) as {
    hooks: Record<string, { hooks: { command: string }[] }[]>
  }
  const command = (ev: Ev): string => settings.hooks[ev]![0]!.hooks[0]!.command
  const dispatcher = (ev: Ev): string => join(root, '.claude/hooks', FILES[ev])
  return { base, root, command, dispatcher }
}

const stubBin = async (script: string) => {
  const bin = await tmpRoot()
  await writeFile(join(bin, 'claude'), `#!/bin/sh\n${script}\n`, { mode: 0o755 })
  return bin
}
const PATHS = (bin: string) => `${bin}:/usr/bin:/bin`

const run = (args: string[], env: Record<string, string> = {}, input = '') =>
  spawnSync('sh', args, {
    encoding: 'utf8',
    input,
    timeout: 20000,
    env: { PATH: '/usr/bin:/bin', ...env },
  })
const shC = (command: string) => run(['-c', command])
const MISSING = (ev: Ev) => `skill not installed: ${SKILLS[ev]}`

describe('ROW-r0-1 shell-safe vault path (command level: sh -c <settings command>)', () => {
  it('ROW-r0-1f control: plain path hook command runs dispatcher', async () => {
    const { command } = await install('plain')
    const r = shC(command('PreCompact'))
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it('ROW-r0-1a space in vault path: hook command runs dispatcher', async () => {
    const { command } = await install('My Vault')
    const r = shC(command('PreCompact'))
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it.each(['SessionStart', 'SessionEnd'] as const)(
    'ROW-r0-1g space in vault path: %s hook command runs dispatcher',
    async ev => {
      const { command } = await install('My Vault')
      const r = shC(command(ev))
      expect(r.status).toBe(0)
      expect(r.stderr).toContain(MISSING(ev))
    },
  )

  it('ROW-r0-1b command substitution in path: hook command has no expansion side effect', async () => {
    const { command } = await install('v$(echo INJECTED 1>&2)')
    const r = shC(command('PreCompact'))
    expect(r.stderr).not.toContain('INJECTED')
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it('ROW-r0-1k backtick in path: hook command has no expansion side effect', async () => {
    const { command } = await install('w`echo INJECTED 1>&2`')
    const r = shC(command('PreCompact'))
    expect(r.stderr).not.toContain('INJECTED')
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it('ROW-r0-1l dollar var in path: hook command does not expand $X', async () => {
    const { command } = await install('lit$X')
    const r = run(['-c', command('PreCompact')], { X: 'zzz' })
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it('ROW-r0-1d single quote in path: hook command runs dispatcher', async () => {
    const { command } = await install("it's mine")
    const r = shC(command('PreCompact'))
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it.each(cases)(
    'ROW-r0-1i %s hook command with double quote / backslash in path (%s)',
    async (ev, name) => {
      const { command } = await install(name)
      const r = shC(command(ev))
      expect(r.status).toBe(0)
      expect(r.stderr).toContain(MISSING(ev))
    },
  )
})

describe('ROW-r0-1 shell-safe vault path (dispatcher level: sh <dispatcher file>)', () => {
  it.each(HOSTILE)('ROW-r0-1c PreCompact dispatcher: no expansion side effect (%s)', async name => {
    const { dispatcher } = await install(name)
    const r = run([dispatcher('PreCompact')])
    expect(r.stderr).not.toContain('INJECTED')
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it.each(['SessionStart', 'SessionEnd'].flatMap(ev => HOSTILE.map(n => [ev as Ev, n] as const)))(
    'ROW-r0-1h %s dispatcher: no expansion side effect (%s)',
    async (ev, name) => {
      const { dispatcher } = await install(name)
      const r = run([dispatcher(ev)])
      expect(r.stderr).not.toContain('INJECTED')
      expect(r.status).toBe(0)
      expect(r.stderr).toContain(MISSING(ev))
    },
  )

  it('ROW-r0-1d2 control: single quote in path, dispatcher works', async () => {
    const { dispatcher } = await install("it's mine")
    const r = run([dispatcher('PreCompact')])
    expect(r.status).toBe(0)
    expect(r.stderr).toContain(MISSING('PreCompact'))
  })

  it.each(cases)(
    'ROW-r0-1j control: %s dispatcher with double quote / backslash in path (%s)',
    async (ev, name) => {
      const { dispatcher } = await install(name)
      const r = run([dispatcher(ev)])
      expect(r.status).toBe(0)
      expect(r.stderr).toContain(MISSING(ev))
    },
  )

  it('ROW-r0-1e dollar var in path: dispatcher ROOT is literal (claude runs in the vault)', async () => {
    const { base, root, dispatcher } = await install('lit$X', [SKILLS.PreCompact])
    const log = join(base, 'cwd.log')
    const bin = await stubBin(`pwd > "$LOG"`)
    run([dispatcher('PreCompact')], { PATH: PATHS(bin), X: 'zzz', LOG: log })
    expect([root, await realpath(root)]).toContain((await waitFor(log)).trim())
  })
})

const recursiveStub = `echo x >> "$COUNT"
n=$(wc -l < "$COUNT")
[ -n "$STAMPF" ] && rm -f "$STAMPF"
if [ "$n" -lt 5 ] && [ -n "$REENTER" ]; then sh "$REENTER" </dev/null; fi
exit 0`

describe('ROW-r0-2 re-entry guard', () => {
  const reenter = async (ev: Ev) => {
    const { base, root, dispatcher } = await install(`guard-${ev}`, [SKILLS[ev]])
    const count = join(base, 'count.log')
    const bin = await stubBin(recursiveStub)
    const d = dispatcher(ev)
    run([d], {
      PATH: PATHS(bin),
      COUNT: count,
      REENTER: d,
      STAMPF: join(root, '.claude/hooks/.last-reflect-day'),
    })
    await waitFor(count)
    await sleep(1000)
    return (await read(count)).trim().split('\n')
  }

  it('ROW-r0-2a SessionStart: nested claude re-firing the dispatcher: stub invoked exactly once', async () => {
    expect(await reenter('SessionStart')).toEqual(['x'])
  })

  it('ROW-r0-2c PreCompact: nested claude re-firing the dispatcher: stub invoked exactly once', async () => {
    expect(await reenter('PreCompact')).toEqual(['x'])
  })

  it('ROW-r0-2d SessionEnd: nested claude re-firing the dispatcher (daily stamp cleared): stub invoked exactly once', async () => {
    expect(await reenter('SessionEnd')).toEqual(['x'])
  })

  const PAIRS = EVENTS.flatMap(x => EVENTS.filter(y => y !== x).map(y => [x, y] as const))
  it.each(PAIRS)(
    'ROW-r0-2e %s nested claude re-fires the %s dispatcher: stub invoked once',
    async (x, y) => {
      const { base, root, dispatcher } = await install(`cross-${x}-${y}`, [
        ...Object.values(SKILLS),
      ])
      const count = join(base, 'count.log')
      const bin = await stubBin(recursiveStub)
      run([dispatcher(x)], {
        PATH: PATHS(bin),
        COUNT: count,
        REENTER: dispatcher(y),
        STAMPF: join(root, '.claude/hooks/.last-reflect-day'),
      })
      await waitFor(count)
      await sleep(1000)
      expect((await read(count)).trim().split('\n')).toEqual(['x'])
    },
  )

  it('ROW-r0-2b control: single trigger without re-entry runs claude once', async () => {
    const { base, dispatcher } = await install('once', [SKILLS.SessionStart])
    const count = join(base, 'count.log')
    const bin = await stubBin(recursiveStub)
    run([dispatcher('SessionStart')], { PATH: PATHS(bin), COUNT: count })
    await waitFor(count)
    await sleep(300)
    expect((await read(count)).trim().split('\n')).toEqual(['x'])
  })
})

describe('ROW-r0-3 PreCompact transcript', () => {
  const exec = async (input: string) => {
    const { base, dispatcher } = await install('pc', [SKILLS.PreCompact])
    const log = join(base, 'argv.log')
    const bin = await stubBin(`{ echo "ARGV: $*"; env; } > "$LOG"`)
    const r = run([dispatcher('PreCompact')], { PATH: PATHS(bin), LOG: log }, input)
    return { r, logged: await waitFor(log) }
  }

  it('ROW-r0-3a transcript_path from stdin payload reaches the skill invocation', async () => {
    const { logged } = await exec(
      JSON.stringify({ session_id: 's1', transcript_path: '/tmp/convo/abc123.jsonl' }),
    )
    expect(logged).toContain('/tmp/convo/abc123.jsonl')
  })

  it('ROW-r0-3b control: empty stdin still invokes the capture skill and exits 0', async () => {
    const { r, logged } = await exec('')
    expect(r.status).toBe(0)
    expect(logged).toContain('ARGV: -p /gilberto-process-capture')
  })

  it('ROW-r0-3c control: valid JSON without transcript_path invokes the capture skill and exits 0', async () => {
    const { r, logged } = await exec(JSON.stringify({ session_id: 's1' }))
    expect(r.status).toBe(0)
    expect(logged).toContain('ARGV: -p /gilberto-process-capture')
  })

  it('ROW-r0-3d transcript_path with space / command substitution reaches claude literally', async () => {
    const tp = '/tmp/a b/$(echo INJECTED 1>&2).jsonl'
    const { r, logged } = await exec(JSON.stringify({ transcript_path: tp }))
    expect(r.stderr).not.toContain('INJECTED')
    expect(logged).toContain(tp)
  })

  it('ROW-r0-3e transcript_path with quotes and backslash reaches claude decoded', async () => {
    const tp = '/tmp/it\'s "q" \\ x.jsonl'
    const { r, logged } = await exec(JSON.stringify({ transcript_path: tp }))
    expect(r.stderr).not.toContain('INJECTED')
    expect(logged).toContain(tp)
  })

  it.each(['not json {', '{"transcript_path": "/tmp/tr'])(
    'ROW-r0-3f control: non-JSON / truncated stdin (%s) still invokes the capture skill and exits 0',
    async input => {
      const { r, logged } = await exec(input)
      expect(r.status).toBe(0)
      expect(logged).toContain('ARGV: -p /gilberto-process-capture')
    },
  )
})

describe('marketplace skills without local files', () => {
  it.each(EVENTS)('%s dispatches from the vault with its process arguments', async ev => {
    const { base, root, dispatcher } = await install('My Vault')
    const log = join(base, 'marketplace.log')
    const bin = await stubBin('pwd > "$LOG"; printf "%s\\n" "$@" >> "$LOG"')
    const input = JSON.stringify({ transcript_path: '/tmp/a transcript.jsonl' })
    const result = run([dispatcher(ev)], { PATH: PATHS(bin), LOG: log }, input)
    const logged = await waitFor(log)
    expect(result.status).toBe(0)
    expect(logged).toContain(await realpath(root))
    const args = ev === 'SessionEnd' ? ' day' : ev === 'PreCompact' ? ' /tmp/a transcript.jsonl' : ''
    expect(logged).toContain(`/${SKILLS[ev]}${args}`)
  })
})
