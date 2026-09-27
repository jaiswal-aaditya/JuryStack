import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import {
  assignments,
  balanceAssignments,
  createAssignment,
  createInvitation,
  createRubric,
  deleteAssignment,
  invitations,
  judges,
  rubrics,
} from './api'
import { events, gallery } from '../tier1/api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'
import { ConfirmDialog } from '../../shared/ConfirmDialog'

const seededCriteria = [
  'Functionality|How completely it works|1|5|1',
  'Quality|Design and implementation quality|1|5|1',
  'Innovation|Originality of the approach|1|5|1',
].join('\n')

function parseCriteria(value: string) {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [
        label,
        description = '',
        minimum = '1',
        maximum = '5',
        weight = '1',
      ] = line.split('|')
      return {
        label,
        description,
        minimum_score: Number(minimum),
        maximum_score: Number(maximum),
        weight: Number(weight),
        display_order: index + 1,
      }
    })
}

export function OrganizerJudgingPage() {
  const queryClient = useQueryClient()
  const eventQuery = useQuery({ queryKey: ['events'], queryFn: events })
  const [eventId, setEventId] = useState('')
  const selectedEventId = eventId || eventQuery.data?.[0]?.id || ''
  const selectedEvent = eventQuery.data?.find(
    (event) => event.id === selectedEventId,
  )
  const rubricQuery = useQuery({
    queryKey: ['rubrics', selectedEventId],
    queryFn: () => rubrics(selectedEventId),
    enabled: Boolean(selectedEventId),
  })
  const inviteQuery = useQuery({
    queryKey: ['judge-invitations', selectedEventId],
    queryFn: () => invitations(selectedEventId),
    enabled: Boolean(selectedEventId),
  })
  const judgeQuery = useQuery({
    queryKey: ['judges', selectedEventId],
    queryFn: () => judges(selectedEventId),
    enabled: Boolean(selectedEventId),
  })
  const assignmentQuery = useQuery({
    queryKey: ['judge-assignments', selectedEventId],
    queryFn: () => assignments(selectedEventId),
    enabled: Boolean(selectedEventId),
  })
  const projectQuery = useQuery({
    queryKey: ['gallery', 'organizer-judging'],
    queryFn: () => gallery(),
  })
  const [criteriaText, setCriteriaText] = useState(seededCriteria)
  const [email, setEmail] = useState('')
  const [trackIds, setTrackIds] = useState<string[]>([])
  const [inviteLink, setInviteLink] = useState('')
  const [inviteCopied, setInviteCopied] = useState(false)
  const [judgeId, setJudgeId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [reviewCount, setReviewCount] = useState(3)
  const [message, setMessage] = useState('')
  const [removalId, setRemovalId] = useState<string | null>(null)
  const [assignmentSearch, setAssignmentSearch] = useState('')

  const refreshAssignments = () =>
    queryClient.invalidateQueries({
      queryKey: ['judge-assignments', selectedEventId],
    })
  const rubricMutation = useMutation({
    mutationFn: () =>
      createRubric(selectedEventId, parseCriteria(criteriaText)),
    onSuccess: async (rubric) => {
      setMessage(`Rubric version ${rubric.version} is now active.`)
      await queryClient.invalidateQueries({
        queryKey: ['rubrics', selectedEventId],
      })
    },
  })
  const inviteMutation = useMutation({
    mutationFn: () =>
      createInvitation({
        event_id: selectedEventId,
        email,
        track_ids: trackIds,
        expires_in_hours: 24,
      }),
    onSuccess: async (invitation) => {
      setInviteLink(
        `${window.location.origin}${invitation.invitation_url ?? ''}`,
      )
      setInviteCopied(false)
      setMessage('Local single-use judge invitation created.')
      await queryClient.invalidateQueries({
        queryKey: ['judge-invitations', selectedEventId],
      })
    },
  })
  const assignmentMutation = useMutation({
    mutationFn: () => createAssignment(judgeId, projectId),
    onSuccess: async () => {
      setMessage('Judge assigned.')
      await refreshAssignments()
    },
  })
  const balanceMutation = useMutation({
    mutationFn: () => balanceAssignments(selectedEventId, reviewCount),
    onSuccess: async (result) => {
      setMessage(`Balanced batch added ${result.created_count} assignments.`)
      await refreshAssignments()
    },
  })
  const removalMutation = useMutation({
    mutationFn: deleteAssignment,
    onSuccess: refreshAssignments,
  })

  const selectedJudge = judgeQuery.data?.find((judge) => judge.id === judgeId)
  const projects = useMemo(
    () =>
      (projectQuery.data?.items ?? []).filter(
        (project) =>
          project.event_id === selectedEventId &&
          (!selectedJudge ||
            selectedJudge.track_ids.includes(project.track_id)),
      ),
    [projectQuery.data, selectedEventId, selectedJudge],
  )
  const filteredAssignments = useMemo(() => {
    const term = assignmentSearch.trim().toLocaleLowerCase()
    if (!term) return assignmentQuery.data ?? []
    return (assignmentQuery.data ?? []).filter((assignment) =>
      `${assignment.judge_name} ${assignment.project_title} ${assignment.track_name}`
        .toLocaleLowerCase()
        .includes(term),
    )
  }, [assignmentQuery.data, assignmentSearch])
  const loading =
    eventQuery.isLoading ||
    rubricQuery.isLoading ||
    inviteQuery.isLoading ||
    judgeQuery.isLoading ||
    assignmentQuery.isLoading ||
    projectQuery.isLoading
  if (loading) return <Loading label="Loading judging configuration…" />
  const error =
    eventQuery.error ??
    rubricQuery.error ??
    inviteQuery.error ??
    judgeQuery.error ??
    assignmentQuery.error ??
    projectQuery.error
  if (error) return <ErrorState error={error} />
  if (!selectedEvent)
    return <EmptyState>Create an event before configuring judging.</EmptyState>

  const mutationError =
    rubricMutation.error ??
    inviteMutation.error ??
    assignmentMutation.error ??
    balanceMutation.error ??
    removalMutation.error
  return (
    <section className="space-y-10">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Organizer</p>
          <h1 className="mt-2 text-3xl font-bold">Judging setup</h1>
          <p>
            Configure the rubric, invite eligible judges, and manage project
            assignments.
          </p>
        </div>
        <label>
          <span className="field-label">Event</span>
          <select
            onChange={(event) => {
              setEventId(event.target.value)
              setTrackIds([])
              setJudgeId('')
              setProjectId('')
            }}
            value={selectedEventId}
          >
            {eventQuery.data?.map((event) => (
              <option key={event.id} value={event.id}>
                {event.name}
              </option>
            ))}
          </select>
        </label>
        {message && (
          <p className="mt-4 text-emerald-300" role="status">
            {message}
          </p>
        )}
        {mutationError && (
          <div className="mt-4">
            <ErrorState error={mutationError} />
          </div>
        )}
      </div>

      <div className="grid gap-8 xl:grid-cols-2">
        <form
          className="rounded-xl border border-slate-800 bg-slate-900 p-6"
          onSubmit={(event) => {
            event.preventDefault()
            rubricMutation.mutate()
          }}
        >
          <h2 className="text-xl font-semibold">Versioned rubric</h2>
          <p className="mt-2 text-sm text-slate-400">
            One line per criterion: label|description|min|max|weight. Saving
            creates a new version; submitted scorecards keep their original
            version.
          </p>
          <textarea
            aria-label="Rubric criteria"
            className="mt-4 min-h-40 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            onChange={(event) => setCriteriaText(event.target.value)}
            required
            value={criteriaText}
          />
          <button
            className="mt-3 rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950"
            disabled={rubricMutation.isPending}
          >
            Save new rubric version
          </button>
          <ul className="mt-5 space-y-2 text-sm">
            {rubricQuery.data?.map((rubric) => (
              <li
                className="rounded border border-slate-800 p-3"
                key={rubric.id}
              >
                Version {rubric.version} · {rubric.criteria.length} criteria ·{' '}
                {rubric.is_active ? 'active' : 'locked history'}
              </li>
            ))}
          </ul>
        </form>

        <form
          className="rounded-xl border border-slate-800 bg-slate-900 p-6"
          onSubmit={(event) => {
            event.preventDefault()
            inviteMutation.mutate()
          }}
        >
          <h2 className="text-xl font-semibold">Invite a local judge</h2>
          <label className="mt-4 block">
            <span className="field-label">Judge email</span>
            <input
              onChange={(event) => setEmail(event.target.value)}
              placeholder="judge@example.org"
              required
              type="email"
              value={email}
            />
          </label>
          <fieldset className="mt-4">
            <legend className="text-sm text-slate-300">Eligible tracks</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {selectedEvent.tracks.map((track) => (
                <label key={track.id} className="text-sm">
                  <input
                    checked={trackIds.includes(track.id)}
                    className="mr-2"
                    onChange={(event) =>
                      setTrackIds((current) =>
                        event.target.checked
                          ? [...current, track.id]
                          : current.filter((id) => id !== track.id),
                      )
                    }
                    type="checkbox"
                  />
                  {track.name}
                </label>
              ))}
            </div>
          </fieldset>
          <button
            className="mt-4 rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
            disabled={trackIds.length === 0 || inviteMutation.isPending}
          >
            Create 24-hour invitation
          </button>
          {inviteLink && (
            <div className="invite-output">
              <output>{inviteLink}</output>
              <button
                className="button button-secondary button-small"
                onClick={() =>
                  void navigator.clipboard.writeText(inviteLink).then(() => {
                    setInviteCopied(true)
                    window.setTimeout(() => setInviteCopied(false), 1800)
                  })
                }
                type="button"
              >
                {inviteCopied ? 'Copied! ✓' : 'Copy link'}
              </button>
            </div>
          )}
          <ul className="mt-5 space-y-2 text-sm">
            {inviteQuery.data?.map((invite) => (
              <li key={invite.id}>
                {invite.email} ·{' '}
                {invite.accepted_by_user_id
                  ? 'accepted'
                  : `expires ${new Date(invite.expires_at).toLocaleString()}`}
              </li>
            ))}
          </ul>
        </form>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-xl font-semibold">Assignments</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          <label>
            <span className="field-label">Judge</span>
            <select
              onChange={(event) => {
                setJudgeId(event.target.value)
                setProjectId('')
              }}
              value={judgeId}
            >
              <option value="">Choose a judge</option>
              {judgeQuery.data?.map((judge) => (
                <option key={judge.id} value={judge.id}>
                  {judge.display_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Eligible project</span>
            <select
              onChange={(event) => setProjectId(event.target.value)}
              value={projectId}
            >
              <option value="">Choose an eligible project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.title} · {project.track_name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="rounded border border-cyan-500 px-4 py-2 text-cyan-300 disabled:opacity-50"
            disabled={!judgeId || !projectId || assignmentMutation.isPending}
            onClick={() => assignmentMutation.mutate()}
            type="button"
          >
            Assign
          </button>
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <label>
            Reviews per project{' '}
            <input
              className="ml-2 w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1"
              min={1}
              max={20}
              onChange={(event) => setReviewCount(Number(event.target.value))}
              type="number"
              value={reviewCount}
            />
          </label>
          <button
            className="rounded border border-cyan-500 px-4 py-2 text-cyan-300"
            disabled={balanceMutation.isPending}
            onClick={() => balanceMutation.mutate()}
            type="button"
          >
            Create balanced batch
          </button>
        </div>
        {assignmentQuery.data?.length === 0 && (
          <div className="mt-5">
            <EmptyState>No judges are assigned yet.</EmptyState>
          </div>
        )}
        {(assignmentQuery.data?.length ?? 0) > 0 && (
          <label className="assignment-search">
            <span className="field-label">Filter assignments</span>
            <input
              onChange={(event) => setAssignmentSearch(event.target.value)}
              placeholder="Judge, project, or track"
              type="search"
              value={assignmentSearch}
            />
          </label>
        )}
        {assignmentSearch && filteredAssignments.length === 0 && (
          <div className="mt-5">
            <EmptyState>No assignments match this search.</EmptyState>
          </div>
        )}
        <ul className="mt-5 divide-y divide-slate-800">
          {filteredAssignments.map((assignment) => (
            <li
              className="flex flex-wrap items-center justify-between gap-3 py-3"
              key={assignment.id}
            >
              <span>
                {assignment.judge_name} → {assignment.project_title}{' '}
                <span className="text-sm text-slate-400">
                  ({assignment.track_name})
                </span>
              </span>
              <button
                className="text-sm text-red-300"
                onClick={() => setRemovalId(assignment.id)}
                type="button"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      </div>
      <ConfirmDialog
        open={Boolean(removalId)}
        title="Remove this assignment?"
        description="The judge will no longer see this project. Assignments with an existing scorecard cannot be removed."
        confirmLabel="Remove assignment"
        pending={removalMutation.isPending}
        onCancel={() => setRemovalId(null)}
        onConfirm={() => {
          if (removalId)
            removalMutation.mutate(removalId, {
              onSuccess: () => setRemovalId(null),
            })
        }}
      />
    </section>
  )
}
