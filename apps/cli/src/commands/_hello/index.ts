import type { CommandRegistryEntry } from '../types.js'
import { handleHelloCommand } from './handler.js'
import { helloMetadata } from './metadata.js'
import { parseHelloCommand, type HelloCommandConfig } from './parser.js'

export const helloCommand: CommandRegistryEntry<HelloCommandConfig> = {
  name: '_hello',
  metadata: helloMetadata,
  parse: parseHelloCommand,
  handle: handleHelloCommand,
}

export { handleHelloCommand, helloMetadata, parseHelloCommand }
export type { HelloCommandConfig }
