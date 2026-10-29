import type { CommandMetadata } from '../types.js'

export const helloMetadata = {
  name: '_hello',
  description: 'admin smoke command',
  usage: '--name <name>',
  options: [{ flags: '--name <name>', description: 'name to greet', required: true }],
  examples: ['gilberto _hello --name Gianluca'],
  notes: ['internal command: underscore prefix marks admin/smoke commands'],
} as const satisfies CommandMetadata
