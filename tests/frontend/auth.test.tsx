import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  renderLoginFlow,
  screen,
  userEvent,
  waitFor,
} from '../../src/frontend/src/test/auth-testing'

afterEach(() => vi.unstubAllGlobals())

describe('authentication flow', () => {
  it('logs in through the API and navigates without handling the cookie itself', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        Response.json({
          id: 'usr_participant',
          email: 'person@example.test',
          display_name: 'Person',
          role: 'participant',
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderLoginFlow()

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith('/api/auth/me', {
        credentials: 'same-origin',
      }),
    )
    await user.type(screen.getByLabelText('Email'), 'person@example.test')
    await user.type(
      screen.getByLabelText('Password'),
      'correct horse battery staple',
    )
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(
      await screen.findByRole('heading', { name: 'Portal home' }),
    ).toBeVisible()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
      }),
    )
  })
})
