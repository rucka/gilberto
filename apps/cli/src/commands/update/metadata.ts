import type { CommandMetadata } from '../types.js'

export const updateMetadata = {
  name: 'update',
  description: 'update the installed vault to the latest gilberto release',
  usage: '[options]',
  options: [{ flags: '--dry-run', description: 'show what would change without writing' }],
  examples: ['gilberto update', 'gilberto update --dry-run'],
  notes: ['placeholder: real implementation tracked in issue #25'],
} as const satisfies CommandMetadata
