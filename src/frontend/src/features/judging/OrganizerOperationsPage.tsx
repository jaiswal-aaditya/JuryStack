import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import {
  auditEvents,
  judges,
  organizerProgress,
  organizerRankings,
} from './api'
import { events, gallery } from '../tier1/api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'

export function OrganizerOperationsPage() {
  const eventQuery = useQuery({ queryKey: ['events'], queryFn: events })
  const [eventId, setEventId] = useState('')
  const selectedEventId = eventId || eventQuery.data?.[0]?.id || ''
  const [trackId, setTrackId] = useState('')
  const [judgeId, setJudgeId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [completionState, setCompletionState] = useState('')
  const [auditEventId, setAuditEventId] = useState('')
  const [auditActorId, setAuditActorId] = useState('')
  const [auditAction, setAuditAction] = useState('')
  const judgeQuery = useQuery({
    queryKey: ['judges', selectedEventId],
    queryFn: () => judges(selectedEventId),
    enabled: Boolean(selectedEventId),
  })
  const projectQuery = useQuery({
    queryKey: ['gallery', 'operations'],
    queryFn: () => gallery(),
  })
  const progressQuery = useQuery({
    queryKey: [
      'organizer-progress',
      selectedEventId,
      trackId,
      judgeId,
      projectId,
      completionState,
    ],
    queryFn: () =>
      organizerProgress(selectedEventId, {
        track_id: trackId,
        judge_id: judgeId,
        project_id: projectId,
        completion_state: completionState,
      }),
    enabled: Boolean(selectedEventId),
  })
  const rankingQuery = useQuery({
    queryKey: ['organizer-rankings', selectedEventId],
    queryFn: () => organizerRankings(selectedEventId),
    enabled: Boolean(selectedEventId),
  })
  const auditQuery = useQuery({
    queryKey: ['audit-events', auditEventId, auditActorId, auditAction],
    queryFn: () =>
      auditEvents({
        event_id: auditEventId,
        actor_id: auditActorId,
        action: auditAction,
      }),
  })
  const selectedEvent = eventQuery.data?.find(
    (event) => event.id === selectedEventId,
  )
  const projects = (projectQuery.data?.items ?? []).filter(
    (project) => project.event_id === selectedEventId,
  )
  const trackProgress = useMemo(() => {
    const grouped = new Map<
      string,
      { name: string; total: number; submitted: number; draft: number }
    >()
    for (const assignment of progressQuery.data?.assignments ?? []) {
      const current = grouped.get(assignment.track_id) ?? {
        name: assignment.track_name,
        total: 0,
        submitted: 0,
        draft: 0,
      }
      current.total += 1
      if (assignment.completion_state === 'submitted') current.submitted += 1
      if (assignment.completion_state === 'draft') current.draft += 1
      grouped.set(assignment.track_id, current)
    }
    return [...grouped.values()].sort((a, b) => a.name.localeCompare(b.name))
  }, [progressQuery.data?.assignments])
  const loading =
    eventQuery.isLoading ||
    judgeQuery.isLoading ||
    projectQuery.isLoading ||
    progressQuery.isLoading ||
    rankingQuery.isLoading ||
    auditQuery.isLoading
  if (loading) return <Loading label="Loading judging operations…" />
  const error =
    eventQuery.error ??
    judgeQuery.error ??
    projectQuery.error ??
    progressQuery.error ??
    rankingQuery.error ??
    auditQuery.error
  if (error) return <ErrorState error={error} />
  if (!selectedEvent)
    return <EmptyState>Create an event before monitoring judging.</EmptyState>
  const summary = progressQuery.data?.summary
  const insufficient = progressQuery.data?.projects.filter(
    (project) => project.is_insufficient,
  )

  return (
    <section className="space-y-8">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Organizer</p>
          <h1>Judging operations</h1>
          <p>
            Monitor coverage, export migration-safe results, and inspect audit
            history.
          </p>
        </div>
        <a
          className="button button-primary"
          href={`/api/organizer/results.csv?event_id=${encodeURIComponent(selectedEventId)}`}
        >
          Export results CSV
        </a>
      </div>

      <div className="grid gap-3 md:grid-cols-5">
        <label>
          <span className="field-label">Event</span>
          <select
            value={selectedEventId}
            onChange={(e) => setEventId(e.target.value)}
          >
            {eventQuery.data?.map((event) => (
              <option key={event.id} value={event.id}>
                {event.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Track</span>
          <select
            aria-label="Track filter"
            value={trackId}
            onChange={(e) => setTrackId(e.target.value)}
          >
            <option value="">All tracks</option>
            {selectedEvent.tracks.map((track) => (
              <option key={track.id} value={track.id}>
                {track.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Judge</span>
          <select
            aria-label="Judge filter"
            value={judgeId}
            onChange={(e) => setJudgeId(e.target.value)}
          >
            <option value="">All judges</option>
            {judgeQuery.data?.map((judge) => (
              <option key={judge.id} value={judge.id}>
                {judge.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Project</span>
          <select
            aria-label="Project filter"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Completion</span>
          <select
            aria-label="Completion filter"
            value={completionState}
            onChange={(e) => setCompletionState(e.target.value)}
          >
            <option value="">All states</option>
            <option value="missing">Missing</option>
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
          </select>
        </label>
      </div>

      <div className="metrics-grid">
        <div className="metric">
          <strong>{summary?.total_assignments ?? 0}</strong>
          <span>Assignments</span>
          <small>Current filters</small>
        </div>
        <div className="metric">
          <strong>{summary?.draft_scorecards ?? 0}</strong>
          <span>Draft</span>
          <small>{summary?.missing_scorecards ?? 0} missing</small>
        </div>
        <div className="metric">
          <strong>{summary?.submitted_scorecards ?? 0}</strong>
          <span>Submitted</span>
          <small>{summary?.completion_percentage ?? 0}% complete</small>
        </div>
        <div className="metric">
          <strong>{summary?.insufficient_project_count ?? 0}</strong>
          <span>Coverage gaps</span>
          <small>Below 3 submitted reviews</small>
        </div>
      </div>

      <section className="track-progress-section" aria-labelledby="track-progress-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">At a glance</p>
            <h2 id="track-progress-title">Review progress by track</h2>
          </div>
          <span>Based on current filters</span>
        </div>
        {trackProgress.length === 0 ? (
          <EmptyState>No assignments match these filters yet.</EmptyState>
        ) : (
          <div className="track-progress-grid">
            {trackProgress.map((track) => {
              const percent = track.total
                ? Math.round((track.submitted / track.total) * 100)
                : 0
              return (
                <article className="track-progress-card panel" key={track.name}>
                  <div className="track-progress-heading">
                    <h3>{track.name}</h3>
                    <strong>{percent}%</strong>
                  </div>
                  <div
                    className="progress-track"
                    role="progressbar"
                    aria-label={`${track.name} review completion`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percent}
                  >
                    <span style={{ width: `${percent}%` }} />
                  </div>
                  <div className="track-progress-caption">
                    <span>{track.submitted} of {track.total} submitted</span>
                    <span>{track.draft} in progress</span>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>

      <div className="panel overflow-x-auto">
        <h2>Assignment progress</h2>
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr>
              <th>Judge</th>
              <th>Project</th>
              <th>Track</th>
              <th>Status</th>
              <th>Raw weighted</th>
            </tr>
          </thead>
          <tbody>
            {progressQuery.data?.assignments.map((row) => (
              <tr key={row.assignment_id}>
                <td>{row.judge_name}</td>
                <td>{row.project_title}</td>
                <td>{row.track_name}</td>
                <td>{row.completion_state}</td>
                <td>{row.raw_weighted_score ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2>Insufficient review coverage</h2>
        {insufficient?.length === 0 ? (
          <EmptyState>
            Every visible project meets the review target.
          </EmptyState>
        ) : (
          <ul className="mt-4 space-y-2">
            {insufficient?.map((project) => (
              <li key={project.project_id}>
                {project.project_title} · {project.submitted_reviews}/
                {project.required_reviews} submitted ({project.assigned_reviews}{' '}
                assigned)
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel overflow-x-auto">
        <div>
          <h2>Normalized project ranking</h2>
          <p>
            Paired-overlap median bias · minimum{' '}
            {rankingQuery.data?.minimum_reviews ?? 2} complete reviews
          </p>
        </div>
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Project</th>
              <th>Reviews</th>
              <th>Raw total</th>
              <th>Final value</th>
              <th>Movement</th>
              <th>Explanation</th>
            </tr>
          </thead>
          <tbody>
            {rankingQuery.data?.projects.map((project) => (
              <tr key={project.project_id}>
                <td>{project.rank ?? '—'}</td>
                <td>
                  {project.project_title}
                  {!project.eligible && (
                    <small className="block text-slate-400">
                      {project.eligibility_reason}
                    </small>
                  )}
                </td>
                <td>{project.review_count}</td>
                <td>{project.raw_total?.toFixed(3) ?? '—'}</td>
                <td>{project.final_value?.toFixed(3) ?? '—'}</td>
                <td>
                  {project.rank_movement == null
                    ? '—'
                    : project.rank_movement > 0
                      ? `+${project.rank_movement}`
                      : project.rank_movement}
                </td>
                <td>
                  <details>
                    <summary>Explain this ranking</summary>
                    <p className="my-2 text-slate-400">
                      Raw rank {project.raw_rank ?? '—'}; fallbacks:{' '}
                      {project.fallbacks_used.join(', ') || 'none'}.
                    </p>
                    <ul className="space-y-1">
                      {project.contributions.map((contribution) => (
                        <li key={contribution.review_id}>
                          {contribution.judge_name}: raw weighted total{' '}
                          {contribution.raw_weighted_total}, raw{' '}
                          {contribution.raw_percentage.toFixed(3)}, bias{' '}
                          {contribution.judge_bias.toFixed(3)}, contribution{' '}
                          {contribution.normalized_contribution.toFixed(3)} ·{' '}
                          {contribution.fallback_used}
                        </li>
                      ))}
                    </ul>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2>Audit history</h2>
            <p>Append-only security and workflow events.</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <label>
              <span className="field-label">Audit event</span>
              <select
                aria-label="Audit event filter"
                value={auditEventId}
                onChange={(e) => setAuditEventId(e.target.value)}
              >
                <option value="">All events</option>
                {eventQuery.data?.map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="field-label">Actor ID</span>
              <input
                aria-label="Audit actor filter"
                placeholder="usr_ or jdg_"
                value={auditActorId}
                onChange={(e) => setAuditActorId(e.target.value)}
              />
            </label>
            <label>
              <span className="field-label">Action prefix</span>
              <input
                aria-label="Audit action filter"
                placeholder="results. or judge."
                value={auditAction}
                onChange={(e) => setAuditAction(e.target.value)}
              />
            </label>
          </div>
        </div>
        {auditQuery.data?.length === 0 ? (
          <EmptyState>No audit events match these filters.</EmptyState>
        ) : (
          <ol className="mt-4 divide-y divide-slate-800">
            {auditQuery.data?.map((event) => (
              <li className="py-3" key={event.id}>
                <strong>{event.summary}</strong>
                <div className="text-sm text-slate-400">
                  {event.actor_name ?? 'System'} ·{' '}
                  {new Date(event.occurred_at).toLocaleString()} ·{' '}
                  {event.action}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}
