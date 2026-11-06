import { chmodSync, cpSync, renameSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

chmodSync(fileURLToPath(new URL('../dist/cli.js', import.meta.url)), 0o755)

const dest = fileURLToPath(new URL('../plugins', import.meta.url))
const tmp = `${dest}.${process.pid}.tmp`
cpSync(fileURLToPath(new URL('../../../plugins', import.meta.url)), tmp, {
  recursive: true,
  filter: src => !src.endsWith('.DS_Store'),
})
rmSync(dest, { recursive: true, force: true })
try {
  renameSync(tmp, dest)
} catch {
  rmSync(tmp, { recursive: true, force: true })
}
