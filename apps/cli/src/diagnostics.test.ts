import { describe, expect, it } from 'vitest'
import { diagnose } from './diagnostics.js'

describe('diagnose', () => {
  it('AC-9: returns the placeholder report', () => {
    expect(diagnose()).toEqual({ status: 'placeholder' })
  })
})
