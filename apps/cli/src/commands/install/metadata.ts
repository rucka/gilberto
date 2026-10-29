import type { CommandMetadata } from '../types.js'

export const installMetadata = {
  name: 'install',
  description: 'install the gilberto vault into a target directory',
  usage: '[target] [options]',
  options: [
    {
      flags: '--seed-topics <list>',
      description: 'topic seeds per pillar, e.g. "intelligence=ai,product;pulse=health"',
    },
    { flags: '--non-interactive', description: 'never prompt; use arguments and defaults' },
    { flags: '--no-hooks', description: 'skip installing git/agent hooks' },
    { flags: '--no-launchd', description: 'skip installing launchd agents' },
    { flags: '-v, --verbose', description: 'print one line per wizard decision' },
  ],
  examples: [
    'gilberto install',
    'gilberto install ~/vault --seed-topics "intelligence=ai,product;pulse=health"',
    'gilberto install ~/vault --non-interactive',
  ],
  notes: [
    'wizard steps: 1 target path (default ~/Dropbox/Gilberto/), 2 overwrite check, 3 topic seeds (pulse, intelligence, projects)',
    'exit codes: 0 declined, 1 target is a file, 2 vault exists, 13 not writable, 64 bad/missing input, 130 aborted',
    'steps 1-3 never write to the filesystem; --no-hooks/--no-launchd are parsed only (later steps)',
  ],
} as const satisfies CommandMetadata
