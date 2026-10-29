# Commands

One directory per command under `src/commands/<name>/`:

- `metadata.ts` — `const` typed `CommandMetadata` (`name`, `description`, `usage`, `options`, `examples`, `notes`)
- `parser.ts` — `parseXCommand(options, args) → XCommandConfig` (discriminated union, literal `command: 'x'`)
- `handler.ts` — `handleXCommand(config, deps: CommandDeps) → Promise<void>`
- `index.ts` — re-exports + `xCommand: CommandRegistryEntry<XCommandConfig>`
- `*.test.ts` — colocated tests

## Register

1. Add `xCommand` to `commandRegistry` in `commands/index.ts`.
2. Add a `case 'x'` to `dispatchCommand` in `commands/dispatcher.ts` (exhaustiveness is compile-checked).

Registration happens in `registerCommandsOnProgram`; duplicate names throw at startup.

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
export const fooCommand: CommandRegistryEntry<FooCommandConfig> = {
  name: 'foo',
  metadata: fooMetadata,
  parse: parseFooCommand,
  handle: handleFooCommand,
}
```
