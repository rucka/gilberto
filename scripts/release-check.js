const { readFileSync } = require('node:fs')

const PKGS = ['gilberto', '@foomakers/gilberto-vault-bootstrap']
const NODE_RANGE = '>=22.12.0'

function checkReleaseConfig(config, pre) {
  const errors = []
  const group = (config.fixed ?? []).find(g => g.includes(PKGS[0]))
  if (!group || !PKGS.every(p => group.includes(p)))
    errors.push(`changeset fixed must group ${PKGS.join(' + ')}`)
  if (pre.mode !== 'pre') errors.push(`pre.json mode is '${pre.mode}', expected 'pre'`)
  if (pre.tag !== 'next') errors.push(`pre.json tag is '${pre.tag}', expected 'next'`)
  return errors
}

function checkEngines(manifest) {
  const node = manifest.engines?.node
  return node === NODE_RANGE
    ? []
    : [`${manifest.name}: engines.node is '${node}', expected '${NODE_RANGE}'`]
}

module.exports = { PKGS, checkReleaseConfig, checkEngines }

if (require.main === module) {
  const read = p => JSON.parse(readFileSync(p, 'utf8'))
  const errors = [
    ...checkReleaseConfig(read('.changeset/config.json'), read('.changeset/pre.json')),
    ...checkEngines(read('apps/cli/package.json')),
    ...checkEngines(read('packages/vault-bootstrap/package.json')),
  ]
  if (errors.length) {
    console.error(errors.join('\n'))
    process.exit(1)
  }
  console.log('release-check ok')
}
