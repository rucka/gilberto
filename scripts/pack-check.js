const { execFileSync } = require('node:child_process')
const { mkdtempSync, readdirSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const { join } = require('node:path')
const { checkEngines } = require('./release-check.js')

const targets = [
  { dir: 'apps/cli', name: 'gilberto', bin: { gilberto: 'dist/cli.js' }, files: ['dist/cli.js'] },
  {
    dir: 'packages/vault-bootstrap',
    name: '@foomakers/gilberto-vault-bootstrap',
    files: ['dist/index.js', 'seed'],
  },
]

const tmp = mkdtempSync(join(tmpdir(), 'pack-check-'))
const errors = []
try {
  for (const t of targets) {
    execFileSync('pnpm', ['pack', '--pack-destination', tmp], { cwd: t.dir, stdio: 'pipe' })
  }
  const tarballs = readdirSync(tmp)
  for (const t of targets) {
    const tgz = tarballs.find(f => f.startsWith(t.name.replace('@', '').replace('/', '-') + '-'))
    if (!tgz) {
      errors.push(`${t.name}: tarball not found`)
      continue
    }
    const list = execFileSync('tar', ['-tzf', join(tmp, tgz)], { encoding: 'utf8' }).split('\n')
    const manifest = JSON.parse(
      execFileSync('tar', ['-xzOf', join(tmp, tgz), 'package/package.json'], { encoding: 'utf8' }),
    )
    if (manifest.name !== t.name) errors.push(`${t.name}: packed name is ${manifest.name}`)
    errors.push(...checkEngines(manifest))
    if (/workspace:/.test(JSON.stringify(manifest)))
      errors.push(`${t.name}: workspace: in packed manifest`)
    if (JSON.stringify(manifest.bin ?? null) !== JSON.stringify(t.bin ?? null))
      errors.push(`${t.name}: bin is ${JSON.stringify(manifest.bin)}`)
    for (const f of t.files)
      if (!list.some(l => l === `package/${f}` || l.startsWith(`package/${f}/`)))
        errors.push(`${t.name}: ${f} missing from tarball`)
  }
} finally {
  rmSync(tmp, { recursive: true, force: true })
}

if (errors.length) {
  console.error(errors.join('\n'))
  process.exit(1)
}
console.log('pack-check ok')
