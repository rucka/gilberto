#!/usr/bin/env node

// Validates: (1) workspace `name` ∈ `@gilberto/*`; (2) no cross-workspace
// path imports under `src/`; (3) non-tool workspaces declare ts:check + lint + test.
// Output: `<file>:<line>:<col>  <rule>  <message>`. Exit 0 OK / 1 violations / 2 config.

const fs = require('node:fs')
const path = require('node:path')

const ROOT = path.resolve(__dirname, '..')
const WORKSPACE_FILE = path.join(ROOT, 'pnpm-workspace.yaml')
const REQUIRED_SCRIPTS = ['ts:check', 'lint', 'test']
const TOOL_PREFIX = 'tools/'
const SOURCE_EXTS = new Set(['.ts', '.tsx'])
const IMPORT_RE = /(?:from|import)\s*['"](\.\.\/[^'"\n]+)['"]/g

function fatal(msg) {
  console.error(`config-error: ${msg}`)
  process.exit(2)
}

function readWorkspaceGlobs() {
  let raw
  try {
    raw = fs.readFileSync(WORKSPACE_FILE, 'utf8')
  } catch (err) {
    fatal(`cannot read ${WORKSPACE_FILE}: ${err.message}`)
  }
  const globs = []
  let inPackages = false
  for (const line of raw.split('\n')) {
    if (/^packages:\s*$/.test(line)) {
      inPackages = true
      continue
    }
    if (!inPackages) continue
    const m = line.match(/^\s+-\s+['"]?([^'"\s]+)['"]?\s*$/)
    if (m) globs.push(m[1])
    else if (/^\S/.test(line)) inPackages = false
  }
  if (globs.length === 0) fatal(`no packages globs in ${WORKSPACE_FILE}`)
  return globs
}

function resolveWorkspaces(globs) {
  const dirs = []
  for (const glob of globs) {
    const idx = glob.indexOf('*')
    if (idx === -1) {
      const abs = path.join(ROOT, glob)
      if (fs.existsSync(path.join(abs, 'package.json'))) dirs.push(abs)
      continue
    }
    const parent = path.join(ROOT, glob.slice(0, idx).replace(/\/$/, ''))
    if (!fs.existsSync(parent)) continue
    for (const name of fs.readdirSync(parent)) {
      const abs = path.join(parent, name)
      if (fs.statSync(abs).isDirectory() && fs.existsSync(path.join(abs, 'package.json')))
        dirs.push(abs)
    }
  }
  return dirs.sort()
}

function walkSourceFiles(dir, out) {
  if (!fs.existsSync(dir)) return
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
      walkSourceFiles(abs, out)
    } else if (entry.isFile() && SOURCE_EXTS.has(path.extname(entry.name))) {
      out.push(abs)
    }
  }
}

function crossWorkspaceImportsIn(ws, siblings) {
  const violations = []
  const files = []
  walkSourceFiles(path.join(ws, 'src'), files)
  for (const file of files) {
    const lines = fs.readFileSync(file, 'utf8').split('\n')
    lines.forEach((line, i) => {
      IMPORT_RE.lastIndex = 0
      let m
      while ((m = IMPORT_RE.exec(line)) !== null) {
        const target = path.resolve(path.dirname(file), m[1])
        const sibling = siblings.find(s => target === s || target.startsWith(s + path.sep))
        if (!sibling) continue
        const col = m.index + line.slice(m.index).indexOf(m[1]) + 1
        violations.push({
          file: path.relative(ROOT, file),
          line: i + 1,
          col,
          rule: 'cross-workspace-import',
          message: `imports from sibling workspace "${path.relative(ROOT, sibling)}"`,
        })
      }
    })
  }
  return violations
}

function main() {
  const workspaces = resolveWorkspaces(readWorkspaceGlobs())
  if (workspaces.length === 0) fatal('no workspaces resolved from globs')

  const violations = []
  for (const ws of workspaces) {
    const pkgPath = path.join(ws, 'package.json')
    let pkg
    try {
      pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'))
    } catch (err) {
      fatal(`cannot parse ${pkgPath}: ${err.message}`)
    }
    const relPkg = path.relative(ROOT, pkgPath)

    if (typeof pkg.name !== 'string' || !pkg.name.startsWith('@gilberto/')) {
      violations.push({
        file: relPkg,
        line: 1,
        col: 1,
        rule: 'workspace-name',
        message: `expected "@gilberto/*", got "${pkg.name ?? '<missing>'}"`,
      })
    }

    if (!path.relative(ROOT, ws).startsWith(TOOL_PREFIX)) {
      const scripts = pkg.scripts ?? {}
      const missing = REQUIRED_SCRIPTS.filter(s => typeof scripts[s] !== 'string')
      if (missing.length > 0) {
        violations.push({
          file: relPkg,
          line: 1,
          col: 1,
          rule: 'required-scripts',
          message: `missing script(s): ${missing.join(', ')}`,
        })
      }
    }

    violations.push(
      ...crossWorkspaceImportsIn(
        ws,
        workspaces.filter(w => w !== ws),
      ),
    )
  }

  if (violations.length === 0) {
    console.log(`hygiene: ${workspaces.length} workspace(s) checked — OK`)
    process.exit(0)
  }
  for (const v of violations) console.error(`${v.file}:${v.line}:${v.col}  ${v.rule}  ${v.message}`)
  console.error(
    `hygiene: ${violations.length} violation(s) across ${workspaces.length} workspace(s)`,
  )
  process.exit(1)
}

main()
