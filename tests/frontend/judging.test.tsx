import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  fireEvent,
  cleanup,
  renderJudgeAssignments,
  renderJudgeScorecard,
  renderOrganizerOperations,
  screen,
  waitFor,
} from '../../src/frontend/src/test/judging-testing'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

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

describe('organizer judging operations', () => {
  it('shows progress, coverage gaps, export, and filtered audit history', async () => {
    const responses: Record<string, unknown> = {
      '/api/events': [
        {
          id: 'evt_01',
          name: 'Sample Hack',
          tracks: [{ id: 'trk_01', name: 'Developer tools' }],
          prizes: [],
          custom_questions: [],
          starts_at: null,
          submissions_open: null,
          submissions_close: '2026-03-01T18:00:00Z',
          slug: 'sample',
        },
      ],
      '/api/events/evt_01/judges': [
        {
          id: 'jdg_01',
          email: 'ada@example.org',
          display_name: 'Ada',
          track_ids: ['trk_01'],
        },
      ],
      '/api/public/projects': {
        items: [
          {
            id: 'prj_01',
            event_id: 'evt_01',
            team_id: 'tm_01',
            team_name: 'Nightshift',
            track_id: 'trk_01',
            track_name: 'Developer tools',
            title: 'Quiet Hours',
            summary: 'Summary',
            repo_url: 'https://example.org',
            status: 'submitted',
            submitted_at: '2026-02-01T00:00:00Z',
            custom_answers: [],
          },
        ],
        total: 1,
      },
      '/api/organizer/events/evt_01/progress': {
        summary: {
          total_assignments: 2,
          missing_scorecards: 1,
          draft_scorecards: 0,
          submitted_scorecards: 1,
          completion_percentage: 50,
          insufficient_project_count: 1,
        },
        assignments: [
          {
            assignment_id: 'asg_1',
            judge_id: 'jdg_01',
            judge_name: 'Ada',
            project_id: 'prj_01',
            project_title: 'Quiet Hours',
            team_id: 'tm_01',
            team_name: 'Nightshift',
            track_id: 'trk_01',
            track_name: 'Developer tools',
            completion_state: 'submitted',
            scorecard_id: 'scr_1',
            rubric_version: 1,
            submitted_at: '2026-02-02T00:00:00Z',
            raw_weighted_score: 4.25,
          },
        ],
        projects: [
          {
            project_id: 'prj_01',
            project_title: 'Quiet Hours',
            team_id: 'tm_01',
            team_name: 'Nightshift',
            track_id: 'trk_01',
            track_name: 'Developer tools',
            assigned_reviews: 2,
            submitted_reviews: 1,
            required_reviews: 3,
            is_insufficient: true,
          },
        ],
      },
      '/api/organizer/audit-events': [
        {
          id: 'audit_1',
          event_id: 'evt_01',
          actor_id: 'usr_org',
          actor_name: 'Organizer',
          action: 'results.exported',
          summary: 'results exported',
          detail: { format: 'csv' },
          occurred_at: '2026-09-27T12:00:00Z',
        },
      ],
    }
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(async (input) => {
        const path = String(input)
        const value = responses[path]
        if (value === undefined)
          return Response.json(
            { error: { message: `Missing mock ${path}` } },
            { status: 500 },
          )
        return Response.json(value)
      })
    vi.stubGlobal('fetch', fetchMock)
    renderOrganizerOperations()

    expect(await screen.findByText('Judging operations')).toBeVisible()
    expect(screen.getByText('50% complete')).toBeVisible()
    expect(screen.getByText(/1\/3 submitted/)).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Export results CSV' }),
    ).toHaveAttribute('href', '/api/organizer/results.csv?event_id=evt_01')
    expect(await screen.findByText('results exported')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Completion filter'), {
      target: { value: 'submitted' },
    })
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/organizer/events/evt_01/progress?completion_state=submitted',
        expect.anything(),
      ),
    )
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

  it('confirms before submitting and then locks a complete evaluation', async () => {
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
      comment: '',
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
      .mockResolvedValueOnce(
        Response.json({
          ...saved,
          status: 'submitted',
          submitted_at: '2026-09-27T12:00:00Z',
        }),
      )
      .mockResolvedValueOnce(Response.json(workspace))
    vi.stubGlobal('fetch', fetchMock)
    renderJudgeScorecard()

    fireEvent.change(await screen.findByLabelText('Impact'), {
      target: { value: '4' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit scorecard' }))
    expect(
      screen.getByRole('dialog', { name: 'Submit this evaluation?' }),
    ).toBeVisible()
    fireEvent.click(
      screen.getByRole('button', { name: 'Submit final evaluation' }),
    )

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/judge/scorecards/scr_private/submit',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
  })
})
