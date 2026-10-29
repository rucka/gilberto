import type { CommandMetadata } from '../types.js'

export const statusMetadata = {
  name: 'status',
  description: 'report the installed vault state and drift from the release',
  usage: '[options]',
  options: [],
  examples: ['gilberto status', 'gilberto --json status'],
  notes: [
    'placeholder: real implementation tracked in issue #25',
    'structured output uses the global --json',
  ],
} as const satisfies CommandMetadata
