#!/usr/bin/env node
import { readFileSync, realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import chalk from 'chalk'
import { Command, CommanderError, Option } from 'commander'
import { getLogLevel, LOG_LEVELS, setLogLevel, type LogLevel } from './ui/logger.js'

const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')) as {
  name: string
  version: string
  description: string
}

const EXPECTED_EXIT_CODES = ['commander.helpDisplayed', 'commander.help', 'commander.version']

const banner = (): string => `${chalk.blue(pkg.name)} v${pkg.version}`

type GlobalOpts = { logLevel?: LogLevel; verbose?: boolean; banner: boolean; json?: boolean }

const applyLogLevel = (opts: GlobalOpts): void =>
  setLogLevel(opts.logLevel ?? (opts.verbose ? 'debug' : 'info'))

/** Builds the root Commander program: metadata, global options, pre-action hook. */
export const createProgram = (): Command => {
  const program = new Command()
    .name(chalk.blue(pkg.name))
    .description(pkg.description)
    .version(pkg.version)
    .addOption(new Option('--log-level <level>', 'log level').choices([...LOG_LEVELS]))
    .option('-v, --verbose', 'alias of --log-level debug (deprecated)')
    .option('--no-banner', 'suppress the banner')
    .option('--json', 'structured output (suppresses the banner)')
    .configureHelp({ sortSubcommands: true })
    .exitOverride()

  program.hook('preAction', cmd => {
    const opts = cmd.optsWithGlobals<GlobalOpts>()
    applyLogLevel(opts)
    if (opts.banner && !opts.json) console.error(banner())
  })
  return program
}

/**
 * Parses `argv` (node-style: `[node, script, ...args]`) against `program`.
 * Rejects with CommanderError on help/version/usage errors and with any command error.
 */
export const runCli = async (
  argv: string[] = process.argv,
  program: Command = createProgram(),
): Promise<void> => {
  await program.parseAsync(argv)
  applyLogLevel(program.opts<GlobalOpts>())
}

/**
 * Single async entrypoint: exits 0 on success and on Commander's expected exits
 * (help/version), Commander's own exit code for usage errors, 1 on unexpected errors.
 */
export const main = async (argv: string[] = process.argv, program?: Command): Promise<void> => {
  try {
    await runCli(argv, program)
    process.exit(0)
  } catch (err) {
    if (err instanceof CommanderError) {
      process.exit(EXPECTED_EXIT_CODES.includes(err.code) ? 0 : err.exitCode)
      return
    }
    const e = err instanceof Error ? err : new Error(String(err))
    console.error(`Error: ${e.message}`)
    if (getLogLevel() === 'debug' && e.stack) console.error(e.stack)
    process.exit(1)
  }
}

const isEntry = (): boolean => {
  const script = process.argv[1]
  if (!script) return false
  const self = fileURLToPath(import.meta.url)
  return [script, `${script}.js`].some(p => {
    try {
      return realpathSync(p) === self
    } catch {
      return false
    }
  })
}

if (isEntry()) void main()
