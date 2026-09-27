import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  fireEvent,
  renderJudgeAssignments,
  renderJudgeScorecard,
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

describe('private judge scorecard', () => {
  it('loads an assigned rubric and saves a private draft', async () => {
    const workspace = {
      project: {
        id: 'prj_07',
        event_id: 'evt_01',
        title: 'Dry Harbour',
        summary: 'One line.',
        repo_url: 'https://example.org/repo/07',
        track_id: 'trk_03',
        track_name: 'Accessibility',
        submitted_at: '2026-03-01T04:29:00Z',
      },
      rubric: {
        id: 'rub_v2',
        event_id: 'evt_01',
        version: 2,
        is_active: true,
        criteria: [
          {
            id: 'crit_impact',
            label: 'Impact',
            description: 'Who benefits',
            minimum_score: 1,
            maximum_score: 5,
            weight: 2,
            display_order: 1,
          },
        ],
      },
      scorecard: null,
    }
    const saved = {
      id: 'scr_private',
      judge_id: 'jdg_01',
      project_id: 'prj_07',
      project_title: 'Dry Harbour',
      event_id: 'evt_01',
      track_id: 'trk_03',
      track_name: 'Accessibility',
      rubric_id: 'rub_v2',
      rubric_version: 2,
      status: 'draft',
      comment: 'Private note',
      submitted_at: null,
      criteria: [
        {
          criterion_id: 'crit_impact',
          label: 'Impact',
          description: 'Who benefits',
          minimum_score: 1,
          maximum_score: 5,
          weight: 2,
          display_order: 1,
          score: 4,
        },
      ],
    }
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json(workspace))
      .mockResolvedValueOnce(Response.json(saved))
      .mockResolvedValueOnce(Response.json({ ...workspace, scorecard: saved }))
    vi.stubGlobal('fetch', fetchMock)
    renderJudgeScorecard()

    expect(await screen.findByText('Dry Harbour')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Impact'), {
      target: { value: '4' },
    })
    fireEvent.change(screen.getByLabelText('Private judge comment'), {
      target: { value: 'Private note' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))

    expect(await screen.findByText('Draft scorecard saved.')).toBeVisible()
    const [, request] = fetchMock.mock.calls[1]
    expect(fetchMock.mock.calls[1][0]).toBe(
      '/api/judge/projects/prj_07/scorecard',
    )
    expect(JSON.parse(String(request?.body))).toEqual({
      rubric_id: 'rub_v2',
      comment: 'Private note',
      scores: [{ criterion_id: 'crit_impact', score: 4 }],
    })
  })
})
