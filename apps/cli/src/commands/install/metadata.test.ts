import { describe, expect, it } from 'vitest'
import { installMetadata } from './metadata.js'

describe('install help notes', () => {
  it('does not mark implemented steps 5-6 as pending', () => {
    expect(installMetadata.notes.join('\n')).not.toMatch(/pending #58/)
  })
})
