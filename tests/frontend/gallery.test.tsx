import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  renderGallery,
  screen,
} from '../../src/frontend/src/test/gallery-testing'

afterEach(() => vi.unstubAllGlobals())

describe('public gallery', () => {
  it('shows a loading state followed by a clear empty state', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockImplementation(async () => Response.json({ items: [], total: 0 })),
    )
    renderGallery()

    expect(screen.getByText('Loading projects…')).toBeVisible()
    expect(
      await screen.findByText('No submitted projects match these filters.'),
    ).toBeVisible()
  })
})
