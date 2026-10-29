export type Logger = {
  debug: (msg: string) => void
  info: (msg: string) => void
  warn: (msg: string) => void
  error: (msg: string) => void
}

export type CommandDeps = {
  logger: Logger
  cwd: string
  env: NodeJS.ProcessEnv
  write: (text: string) => void
}

export type CommandOption = {
  flags: string
  description: string
  defaultValue?: string | boolean
  required?: boolean
}

export type CommandMetadata = {
  name: string
  description: string
  usage: string
  options: readonly CommandOption[]
  examples: readonly string[]
  notes: readonly string[]
}

export type CommandOptions = Record<string, unknown>

export type CommandRegistryEntry<C extends { command: string }> = {
  name: C['command']
  metadata: CommandMetadata
  parse: (options: CommandOptions, args: string[]) => C
  handle: (config: C, deps: CommandDeps) => Promise<void>
}
