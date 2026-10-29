export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export const LOG_LEVELS: readonly LogLevel[] = ['debug', 'info', 'warn', 'error']

let current: LogLevel = 'info'

export const setLogLevel = (level: LogLevel): void => {
  current = level
}

export const getLogLevel = (): LogLevel => current

const emit = (level: LogLevel, msg: string): void => {
  if (LOG_LEVELS.indexOf(level) >= LOG_LEVELS.indexOf(current)) console.error(msg)
}

export const debug = (msg: string): void => emit('debug', msg)
export const info = (msg: string): void => emit('info', msg)
export const warn = (msg: string): void => emit('warn', msg)
export const error = (msg: string): void => emit('error', msg)
