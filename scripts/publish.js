// Publishes the fixed group: prerelease (X.Y.Z-ch.N) on dist-tag `next`, final on `latest`.
// Not `changeset publish`: the version is set by release-plan.js, and a prerelease must never move `latest`.
const { execFileSync } = require('node:child_process')
const { PKGS } = require('./release-check.js')

const version = process.argv[2]
const tag = version.includes('-') ? 'next' : 'latest'
const view = (...a) => execFileSync('npm', ['view', ...a], { encoding: 'utf8' }).trim()
const latest = p => {
  try {
    return view(p, 'dist-tags.latest')
  } catch {
    return ''
  }
}
const exists = p => {
  try {
    return view(`${p}@${version}`, 'version') !== ''
  } catch {
    return false
  }
}

const dup = PKGS.filter(exists)
if (dup.length) {
  console.error(`::error::${dup.join(', ')}@${version} already published`)
  process.exit(1)
}
const before = Object.fromEntries(PKGS.map(p => [p, latest(p)]))
execFileSync(
  'pnpm',
  [
    ...PKGS.flatMap(p => ['--filter', p]),
    'publish',
    '--tag',
    tag,
    '--access',
    'public',
    '--no-git-checks',
  ],
  { stdio: 'inherit' },
)
// npm sets `latest` on a package's first publish; on a prerelease an existing `latest` must not move.
const moved = tag === 'next' ? PKGS.filter(p => before[p] && latest(p) !== before[p]) : []
if (moved.length) {
  console.error(`::error::dist-tag latest moved for ${moved.join(', ')}`)
  process.exit(1)
}
console.log(`published ${version} on ${tag}`)
