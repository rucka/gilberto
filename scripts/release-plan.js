// Release version from channel + changesets base + existing tags (pair's dispatch model).
// pre/rc: X.Y.Z-<channel>.N on dist-tag next; final: X.Y.Z on latest. Channels forward-only.
const { execFileSync } = require('node:child_process')

const CHANNELS = ['pre', 'rc', 'final']
const SEMVER = /^v?(\d+)\.(\d+)\.(\d+)(?:-(pre|rc)\.(\d+))?$/
const parse = t => {
  const m = SEMVER.exec(t)
  return (
    m && { core: [+m[1], +m[2], +m[3]], ch: m[4] ?? 'final', n: m[5] === undefined ? -1 : +m[5] }
  )
}
const cmp = (a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]

function plan(channel, base, tags) {
  if (!CHANNELS.includes(channel)) throw new Error(`channel '${channel}' not in ${CHANNELS}`)
  const b = parse(base)
  if (!b || b.ch !== 'final') throw new Error(`base '${base}' is not X.Y.Z`)
  const all = tags.map(parse).filter(Boolean)
  const finals = all.filter(t => t.ch === 'final').map(t => t.core)
  if (finals.some(f => cmp(f, b.core) >= 0))
    throw new Error(`base ${base} is not above the last final release`)
  const same = all.filter(t => cmp(t.core, b.core) === 0)
  const rank = CHANNELS.indexOf(channel)
  if (same.some(t => CHANNELS.indexOf(t.ch) > rank))
    throw new Error(`${channel} is behind an existing release of ${base}`)
  const n = Math.max(-1, ...same.filter(t => t.ch === channel).map(t => t.n)) + 1
  const version = channel === 'final' ? base : `${base}-${channel}.${n}`
  const prerelease = channel !== 'final'
  return { version, tag: `v${version}`, distTag: prerelease ? 'next' : 'latest', prerelease }
}

module.exports = { plan }

if (require.main === module) {
  const [channel, base] = process.argv.slice(2)
  const tags = execFileSync('git', ['tag', '--list', 'v*'], { encoding: 'utf8' }).split('\n')
  try {
    console.log(JSON.stringify(plan(channel, base, tags.filter(Boolean))))
  } catch (e) {
    console.error(`::error::${e.message}`)
    process.exit(1)
  }
}
