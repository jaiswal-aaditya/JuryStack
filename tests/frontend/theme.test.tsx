import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  cleanup,
  renderThemeToggle,
  screen,
  userEvent,
  waitFor,
} from '../../src/frontend/src/test/theme-testing'

beforeEach(() => {
  const values = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    clear: () => values.clear(),
    getItem: (key: string) => values.get(key) ?? null,
    removeItem: (key: string) => values.delete(key),
    setItem: (key: string, value: string) => values.set(key, value),
  })
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  )
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('theme preference', () => {
  it('defaults to system and persists an explicit dark preference', async () => {
    const user = userEvent.setup()
    renderThemeToggle()

    expect(screen.getByRole('button', { name: 'System' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await user.click(screen.getByRole('button', { name: 'Dark' }))

    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe('dark')
      expect(localStorage.getItem('jurystack-theme')).toBe('dark')
    })
  })
})
