# Commands

One directory per command under `src/commands/<name>/`:

- `metadata.ts` — `const` typed `CommandMetadata` (`name`, `description`, `usage`, `options`, `examples`, `notes`)
- `parser.ts` — `parseXCommand(options, args) → XCommandConfig` (discriminated union, literal `command: 'x'`)
- `handler.ts` — `handleXCommand(config, deps: CommandDeps) → Promise<void>`
- `index.ts` — re-exports + `xCommand: CommandRegistryEntry<XCommandConfig>` wrapped in `withOrigin(import.meta.url, {…})` so duplicate-name errors name the real directory
- `*.test.ts` — colocated tests

## Register

Add `xCommand` to `commandRegistry` in `commands/index.ts` (one import + one array entry). `dispatchCommand` routes by `config.command` to the entry's `handle`; no dispatcher edit.

Registration happens in `registerCommandsOnProgram`; duplicate names throw at startup, naming both directories.

Options reach `parse` camelCased (`--log-level` → `logLevel`); positionals are filtered with `onlyStrings`.
Commands starting with `_` are internal/admin.

## Skeleton

```ts
// metadata.ts
export const fooMetadata = {
  name: 'foo',
  description: '…',
  usage: '--bar <bar>',
  options: [{ flags: '--bar <bar>', description: '…', required: true }],
  examples: ['gilberto foo --bar x'],
  notes: [],
} as const satisfies CommandMetadata

// parser.ts
export type FooCommandConfig = { command: 'foo'; bar: string }
export const parseFooCommand = (options: CommandOptions, _args: string[]): FooCommandConfig => ({
  command: 'foo',
  bar: String(options['bar']),
})

// handler.ts
export const handleFooCommand = async (config: FooCommandConfig, deps: CommandDeps): Promise<void> => {
  deps.write(`${config.bar}\n`)
}

// index.ts
export const fooCommand: CommandRegistryEntry<FooCommandConfig> = withOrigin(import.meta.url, {
  name: 'foo',
  metadata: fooMetadata,
  parse: parseFooCommand,
  handle: handleFooCommand,
})
```

## Sub-actions

A command may declare `metadata.subcommands` (`name`, `description`, `usage`, `options`); each becomes a Commander sub-command of the entry. `parse` receives `[subName, ...positionals]`. The parent gets no action: bare `<cmd>` prints help. See `plugin/`.
