import chalk from 'chalk'

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export const LOG_LEVELS: readonly LogLevel[] = ['debug', 'info', 'warn', 'error']

const COLOURS: Record<LogLevel, (s: string) => string> = {
  debug: s => chalk.gray(s),
  info: s => chalk.blue(s),
  warn: s => chalk.yellow(s),
  error: s => chalk.red(s),
}

let current: LogLevel = 'info'

export const isLogLevel = (v: unknown): v is LogLevel => LOG_LEVELS.includes(v as LogLevel)

export const setLogLevel = (level: LogLevel): void => {
  current = level
}

export const getLogLevel = (): LogLevel => current

// All output goes to stderr: stdout is reserved for command data.
const emit = (level: LogLevel, msg: string): void => {
  if (LOG_LEVELS.indexOf(level) >= LOG_LEVELS.indexOf(current)) console.error(COLOURS[level](msg))
}

export const debug = (msg: string): void => emit('debug', msg)
export const info = (msg: string): void => emit('info', msg)
export const warn = (msg: string): void => emit('warn', msg)
export const error = (msg: string): void => emit('error', msg)

export const logger = { debug, info, warn, error }

/**
 * Effective level: flag > `GILBERTO_LOG_LEVEL` > `info`.
 * An invalid env value falls back to `info` with a single warn line (unless `warnInvalid` is false).
 */
export const resolveLogLevel = (
  flag?: string,
  env: NodeJS.ProcessEnv = process.env,
  warnInvalid = true,
): LogLevel => {
  if (isLogLevel(flag)) return flag
  const raw = env['GILBERTO_LOG_LEVEL']
  if (isLogLevel(raw)) return raw
  if (raw && warnInvalid) warn(`ignored invalid GILBERTO_LOG_LEVEL='${raw}'`)
  return 'info'
}
