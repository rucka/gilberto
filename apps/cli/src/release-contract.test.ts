import { spawnSync } from 'node:child_process'
import { chmodSync, existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { delimiter, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const require = createRequire(import.meta.url)
const { checkReleaseConfig, checkEngines } = require(join(root, 'scripts/release-check.js')) as {
  checkReleaseConfig: (c: unknown, preExists: boolean) => string[]
  checkEngines: (m: unknown) => string[]
}
const { plan } = require(join(root, 'scripts/release-plan.js')) as {
  plan: (
    channel: string,
    base: string,
    tags: string[],
  ) => { version: string; tag: string; distTag: string; prerelease: boolean }
}
const readJson = (p: string): Record<string, unknown> =>
  JSON.parse(readFileSync(join(root, p), 'utf8')) as Record<string, unknown>
const config = readJson('.changeset/config.json')
const preExists = existsSync(join(root, '.changeset/pre.json'))
const PKGS = ['gilberto', '@foomakers/gilberto-vault-bootstrap']

describe('release config (AC2/AC3, r0-4)', () => {
  it('real config passes', () => expect(checkReleaseConfig(config, preExists)).toEqual([]))
  it.each([
    ['fixed empty', { ...config, fixed: [] }, false],
    ['fixed partial', { ...config, fixed: [['gilberto']] }, false],
    ['fixed split', { ...config, fixed: [['gilberto'], [PKGS[1]]] }, false],
    ['changesets pre mode', config, true],
  ])('%s fails', (_n, c, p) => expect(checkReleaseConfig(c, p).length).toBeGreaterThan(0))
})

describe('release plan (channels pre/rc/final)', () => {
  it.each([
    ['pre', [], '0.1.0-pre.0', 'next'],
    ['pre', ['v0.1.0-pre.0', 'v0.1.0-pre.1'], '0.1.0-pre.2', 'next'],
    ['rc', ['v0.1.0-pre.3'], '0.1.0-rc.0', 'next'],
    ['final', ['v0.1.0-rc.1'], '0.1.0', 'latest'],
    ['pre', ['v0.0.9', 'v0.1.0-pre.0'], '0.1.0-pre.1', 'next'],
  ])('%s over %j -> %s on %s', (ch, tags, version, distTag) =>
    expect(plan(ch, '0.1.0', tags)).toEqual({
      version,
      tag: `v${version}`,
      distTag,
      prerelease: distTag === 'next',
    }),
  )
  it.each([
    ['unknown channel', 'beta', '0.1.0', []],
    ['backward rc->pre', 'pre', '0.1.0', ['v0.1.0-rc.0']],
    ['base already final', 'pre', '0.1.0', ['v0.1.0']],
    ['base below last final', 'final', '0.1.0', ['v0.2.0']],
    ['base not semver', 'final', '0.1', []],
  ])('%s throws', (_n, ch, base, tags) => expect(() => plan(ch, base, tags)).toThrow())
})

describe('engines (r0-3)', () => {
  it.each(['apps/cli/package.json', 'packages/vault-bootstrap/package.json'])(
    '%s declares node >=22.12.0',
    f => expect(checkEngines(readJson(f))).toEqual([]),
  )
  it.each([{}, { engines: { node: '>=20' } }])('rejects %j', m =>
    expect(checkEngines(m).length).toBeGreaterThan(0),
  )
})

// npm/pnpm stubs: registry state in a JSON file; pnpm publish sets next (and latest per STUB_SET_LATEST)
function runPublish(
  state: Record<string, Record<string, string>>,
  setLatest = '',
  version = '0.1.0-pre.0',
) {
  const dir = mkdtempSync(join(tmpdir(), 'publish-'))
  const stateFile = join(dir, 'state.json')
  writeFileSync(stateFile, JSON.stringify(state))
  const npm = `#!/usr/bin/env node
const fs=require('fs');const s=JSON.parse(fs.readFileSync(process.env.STUB_STATE));
const [,spec,field]=process.argv.slice(2);const at=spec.lastIndexOf('@');
if(field==='version'){const [n,v]=[spec.slice(0,at),spec.slice(at+1)];if(s[n]&&s[n]['v:'+v])console.log(v);process.exit(0)}
const t=(s[spec]||{})[field.replace('dist-tags.','')];if(t)console.log(t)`
  const pnpm = `#!/usr/bin/env node
const fs=require('fs');const f=process.env.STUB_STATE;const s=JSON.parse(fs.readFileSync(f));
fs.appendFileSync(f+'.log',process.argv.slice(2).join(' ')+'\\n');
const a=process.argv.slice(2);const tag=a[a.indexOf('--tag')+1];
for(const n of ${JSON.stringify(PKGS)}){s[n]=s[n]||{};s[n][tag]=process.env.STUB_VERSION;s[n]['v:'+process.env.STUB_VERSION]='1';
if(process.env.STUB_SET_LATEST)s[n].latest=process.env.STUB_SET_LATEST}
fs.writeFileSync(f,JSON.stringify(s))`
  writeFileSync(join(dir, 'npm'), npm)
  writeFileSync(join(dir, 'pnpm'), pnpm)
  chmodSync(join(dir, 'npm'), 0o755)
  chmodSync(join(dir, 'pnpm'), 0o755)
  const r = spawnSync('node', [join(root, 'scripts/publish.js'), version], {
    cwd: root,
    encoding: 'utf8',
    env: {
      ...process.env,
      PATH: dir + delimiter + process.env['PATH'],
      STUB_STATE: stateFile,
      STUB_SET_LATEST: setLatest,
      STUB_VERSION: version,
    },
  })
  let log = ''
  try {
    log = readFileSync(stateFile + '.log', 'utf8')
  } catch {
    /* not called */
  }
  return { status: r.status, log }
}

describe('publish (r0-1/r0-2)', () => {
  it('final publishes both on latest', () => {
    const { status, log } = runPublish({}, '', '0.1.0')
    expect(status).toBe(0)
    expect(log).toMatch(/--tag latest/)
  })
  it('prerelease publishes both with --tag next --access public, exit 0', () => {
    const { status, log } = runPublish({})
    expect(status).toBe(0)
    expect(log).toMatch(/publish/)
    expect(log).toMatch(/--tag next/)
    expect(log).toMatch(/--access public/)
    expect(log).not.toMatch(/changeset/)
  })
  it('fails when latest is moved', () => {
    const state = Object.fromEntries(PKGS.map(n => [n, { latest: '0.0.9' }]))
    expect(runPublish(state, '0.1.0-pre.0').status).not.toBe(0)
  })
  it('fails without publishing when version already exists', () => {
    const state = { gilberto: { 'v:0.1.0-pre.0': '1' } }
    const { status, log } = runPublish(state)
    expect(status).not.toBe(0)
    expect(log).toBe('')
  })
  it('release.yml uses publish.js, not changeset publish', () => {
    const wf = readFileSync(join(root, '.github/workflows/release.yml'), 'utf8')
    expect(wf).toMatch(/node scripts\/publish\.js/)
    expect(wf).not.toMatch(/changeset publish/)
  })
  it('version.yml is dispatch-only (a merge never releases)', () => {
    const wf = readFileSync(join(root, '.github/workflows/version.yml'), 'utf8')
    expect(wf).toMatch(/workflow_dispatch/)
    expect(wf).not.toMatch(/^\s*push:/m)
  })
})
