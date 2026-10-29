import type { CommandMetadata } from '../types.js'

export const installMetadata = {
  name: 'install',
  description: 'install the gilberto vault into a target directory',
  usage: '[target] [options]',
  options: [
    { flags: '--seed-topics', description: 'seed the vault with starter topics' },
    { flags: '--no-hooks', description: 'skip installing git/agent hooks' },
    { flags: '--no-launchd', description: 'skip installing launchd agents' },
    { flags: '-v, --verbose', description: 'verbose output' },
  ],
  examples: [
    'gilberto install',
    'gilberto install ~/vault --seed-topics',
    'gilberto install --no-hooks --no-launchd',
  ],
  notes: [
    'target defaults to the current directory',
    'placeholder: real implementation tracked in issue #10',
  ],
} as const satisfies CommandMetadata
