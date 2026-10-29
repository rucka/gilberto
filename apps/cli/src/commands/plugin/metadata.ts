import type { CommandMetadata } from '../types.js'

export const pluginMetadata = {
  name: 'plugin',
  description: 'manage gilberto plugins',
  usage: '<action> [options]',
  options: [],
  subcommands: [
    { name: 'list', description: 'list installed plugins', usage: '[options]', options: [] },
    { name: 'enable', description: 'enable an installed plugin', usage: '<name>', options: [] },
    { name: 'disable', description: 'disable an installed plugin', usage: '<name>', options: [] },
    {
      name: 'install',
      description: 'install a plugin from a source',
      usage: '<source> [options]',
      options: [{ flags: '--force', description: 'overwrite an existing plugin' }],
    },
    {
      name: 'update',
      description: 'update one or all plugins',
      usage: '[name] [options]',
      options: [{ flags: '--dry-run', description: 'show what would change without writing' }],
    },
    {
      name: 'remove',
      description: 'remove an installed plugin',
      usage: '<name> [options]',
      options: [{ flags: '--purge', description: 'also delete plugin data' }],
    },
  ],
  examples: ['gilberto plugin list', 'gilberto plugin install ./my-plugin --force'],
  notes: ['placeholder: real implementation tracked in issue #15'],
} as const satisfies CommandMetadata
