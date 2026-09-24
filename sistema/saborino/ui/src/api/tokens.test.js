import { describe, expect, it, vi } from 'vitest'
import { purgeLegacyTokens } from './tokens'

describe('purgeLegacyTokens', () => {
  it('remove somente as duas chaves legadas', () => {
    const storage = { removeItem: vi.fn() }
    purgeLegacyTokens(storage)
    expect(storage.removeItem.mock.calls).toEqual([
      ['saborino_access'], ['saborino_refresh'],
    ])
  })
})
