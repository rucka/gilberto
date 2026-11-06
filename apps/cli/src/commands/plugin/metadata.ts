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
      usage: '<name|repo-url> [options]',
      options: [
        { flags: '--force', description: 'overwrite an already installed plugin' },
        { flags: '--dry-run', description: 'show what would change without writing' },
      ],
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
      options: [
        { flags: '--purge', description: 'also delete user-modified contributions' },
        { flags: '--dry-run', description: 'show what would change without writing' },
      ],
    },
  ],
  examples: ['gilberto plugin list', 'gilberto plugin install gilberto-core --dry-run'],
  notes: [
    'install/remove run in the current directory, which must be a vault',
    'skills are never copied: install them with /plugin install <name>',
    'list/enable/disable/update are placeholders (issue #15)',
  ],
} as const satisfies CommandMetadata
