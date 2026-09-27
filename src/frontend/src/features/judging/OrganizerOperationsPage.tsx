import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { auditEvents, judges, organizerProgress } from './api'
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
  const loading =
    eventQuery.isLoading ||
    judgeQuery.isLoading ||
    projectQuery.isLoading ||
    progressQuery.isLoading ||
    auditQuery.isLoading
  if (loading) return <Loading label="Loading judging operations…" />
  const error =
    eventQuery.error ??
    judgeQuery.error ??
    projectQuery.error ??
    progressQuery.error ??
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
