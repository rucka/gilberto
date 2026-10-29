import type { Command } from 'commander'
import type {
  CommandDeps,
  CommandMetadata,
  CommandOption,
  CommandOptions,
  CommandRegistryEntry,
} from './types.js'

const camel = (key: string): string => key.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase())

export const normalizeOptionKeys = (opts: CommandOptions): CommandOptions =>
  Object.fromEntries(Object.entries(opts).map(([k, v]) => [camel(k), v]))

export const onlyStrings = (args: readonly unknown[]): string[] =>
  args.filter((a): a is string => typeof a === 'string')

export const addCommandOptions = (command: Command, options: readonly CommandOption[]): Command => {
  for (const { flags, description, defaultValue, required } of options) {
    if (required) command.requiredOption(flags, description, defaultValue as string | undefined)
    else command.option(flags, description, defaultValue as string | undefined)
  }
  return command
}

const helpBlock = (title: string, lines: readonly string[]): string =>
  lines.length ? `\n${title}:\n${lines.map(l => `  ${l}`).join('\n')}\n` : ''

export const registerCommandFromMetadata = <C extends { command: string }>(
  program: Command,
  entry: CommandRegistryEntry<C>,
  deps: CommandDeps,
  dispatch: (config: C, deps: CommandDeps) => Promise<void>,
): Command => {
  const { name, description, usage, options, examples, notes }: CommandMetadata = entry.metadata
  if (program.commands.some(c => c.name() === name))
    throw new Error(`command "${name}" already registered`)
  const cmd = program.command(name).description(description).usage(usage)
  addCommandOptions(cmd, options)
  cmd.addHelpText('after', helpBlock('Examples', examples) + helpBlock('Notes', notes))
  return cmd.action(async (...actionArgs: unknown[]) => {
    const self = actionArgs.at(-1) as Command
    await dispatch(entry.parse(normalizeOptionKeys(self.opts()), onlyStrings(self.args)), deps)
  })
}
