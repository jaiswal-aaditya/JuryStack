import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  renderJudgeAssignments,
  screen,
} from '../../src/frontend/src/test/judging-testing'

afterEach(() => vi.unstubAllGlobals())

describe('judge assignments', () => {
  it('shows loading and empty states for a judge with no assignments', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(Response.json([])),
    )
    renderJudgeAssignments()

    expect(screen.getByText('Loading your assignments…')).toBeVisible()
    expect(
      await screen.findByText('No projects have been assigned to you.'),
    ).toBeVisible()
  })

  it('shows a backend authorization error clearly', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(
        Response.json(
          {
            error: { message: 'You do not have permission for this action.' },
          },
          { status: 403 },
        ),
      ),
    )
    renderJudgeAssignments()

    expect(
      await screen.findByText('You do not have permission for this action.'),
    ).toBeVisible()
  })
})
