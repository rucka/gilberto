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
    { flags: '--no-hooks', description: 'skip installing .claude hooks (step 7)' },
    { flags: '--no-launchd', description: 'skip writing launchd plists (step 8)' },
    { flags: '--launchd-in-ci', description: 'write launchd plists even when CI=true (macOS)' },
    { flags: '-v, --verbose', description: 'print one line per wizard decision' },
  ],
  examples: [
    'gilberto install',
    'gilberto install ~/vault --seed-topics "intelligence=ai,product;pulse=health"',
    'gilberto install ~/vault --non-interactive',
  ],
  notes: [
    'wizard steps: 1 target path (default ~/Dropbox/Gilberto/), 2 overwrite check, 3 topic seeds (pulse, intelligence, projects), 4 vault skeleton (temp dir, atomic move), 7 .claude hooks (settings.json merge), 8 launchd plists (macOS; linux stub)',
    'exit codes: 0 declined, 1 target is a file, 2 vault exists, 13 not writable, 28 disk full, 64 bad/missing input, 65 invalid settings.json or plist/plutil failure, 70 vault-bootstrap missing, 130 aborted',
    'steps 1-3 never write; step 4 writes in a temp dir and moves it atomically to the target; steps 7-8 run on the written vault, plists are written but never loaded (no launchctl)',
  ],
} as const satisfies CommandMetadata
