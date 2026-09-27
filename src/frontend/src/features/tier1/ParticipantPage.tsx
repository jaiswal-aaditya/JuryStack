import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import {
  acceptInvite,
  createInvite,
  createTeam,
  events,
  myProjects,
  teams,
} from './api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'
import { useToast } from '../../shared/toast-context'

export function ParticipantPage() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const eventQuery = useQuery({ queryKey: ['events'], queryFn: events })
  const teamQuery = useQuery({ queryKey: ['teams'], queryFn: teams })
  const projectQuery = useQuery({
    queryKey: ['my-projects'],
    queryFn: myProjects,
  })
  const [teamName, setTeamName] = useState('')
  const [eventId, setEventId] = useState('')
  const [token, setToken] = useState(
    () => new URLSearchParams(window.location.search).get('invite') ?? '',
  )
  const [inviteUrl, setInviteUrl] = useState('')
  const [inviteCopied, setInviteCopied] = useState(false)
  const [message, setMessage] = useState('')

  const refreshTeams = () =>
    queryClient.invalidateQueries({ queryKey: ['teams'] })
  const createTeamMutation = useMutation({
    mutationFn: (input: { eventId: string; name: string }) =>
      createTeam(input.eventId, input.name),
    onSuccess: async () => {
      setTeamName('')
      setMessage('Team created.')
      await refreshTeams()
    },
  })
  const acceptMutation = useMutation({
    mutationFn: () => acceptInvite(token),
    onSuccess: async () => {
      setToken('')
      setMessage('Invite accepted. Welcome to the team.')
      await refreshTeams()
    },
  })

  if (teamQuery.isLoading || eventQuery.isLoading || projectQuery.isLoading) {
    return <Loading label="Loading your workspace…" />
  }
  const error = teamQuery.error ?? eventQuery.error ?? projectQuery.error
  if (error) return <ErrorState error={error} />
  const chosenEvent = eventId || eventQuery.data?.[0]?.id || ''

  return (
    <section className="workspace-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Participant</p>
          <h1 className="mt-2 text-3xl font-bold">Your teams and projects</h1>
          <p className="mt-3 text-slate-400">
            Create a team, invite collaborators, and manage submissions.
          </p>
        </div>
        {(teamQuery.data?.length ?? 0) > 0 && (
          <Link className="button button-primary" to="/workspace/projects/new">
            New project
          </Link>
        )}
      </div>
      {message && (
        <p
          role="status"
          className="mt-5 rounded bg-emerald-950 p-3 text-emerald-200"
        >
          {message}
        </p>
      )}
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <form
          className="panel p-5"
          onSubmit={(event) => {
            event.preventDefault()
            createTeamMutation.mutate({ eventId: chosenEvent, name: teamName })
          }}
        >
          <h2 className="text-xl font-semibold">Create a team</h2>
          <label className="mt-4 block">
            <span className="field-label">Event</span>
            <select
              onChange={(event) => setEventId(event.target.value)}
              value={chosenEvent}
            >
              {eventQuery.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="mt-3 block">
            <span className="field-label">Team name</span>
            <input
              onChange={(event) => setTeamName(event.target.value)}
              placeholder="e.g. NorthKiln"
              required
              value={teamName}
            />
          </label>
          {createTeamMutation.error && (
            <ErrorState error={createTeamMutation.error} />
          )}
          <button
            className="button button-secondary mt-3"
            disabled={!chosenEvent || createTeamMutation.isPending}
          >
            Create team
          </button>
        </form>
        <form
          className="panel p-5"
          onSubmit={(event) => {
            event.preventDefault()
            acceptMutation.mutate()
          }}
        >
          <h2 className="text-xl font-semibold">Join with an invite</h2>
          <label className="mt-4 block">
            <span className="field-label">Invite token</span>
            <input
              onChange={(event) => setToken(event.target.value)}
              placeholder="Paste invite token"
              required
              value={token}
            />
          </label>
          {acceptMutation.error && <ErrorState error={acceptMutation.error} />}
          <button
            className="button button-secondary mt-3"
            disabled={acceptMutation.isPending}
          >
            Join team
          </button>
        </form>
      </div>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Collaboration</p>
          <h2>Teams</h2>
        </div>
        <span>{teamQuery.data?.length ?? 0} total</span>
      </div>
      {teamQuery.data?.length === 0 && (
        <EmptyState>You do not belong to a team yet.</EmptyState>
      )}
      <ul className="mt-4 grid gap-4 md:grid-cols-2">
        {teamQuery.data?.map((team) => (
          <li className="panel team-card" key={team.id}>
            <div className="team-card-title">
              <span className="quick-icon">
                {team.name.slice(0, 1).toUpperCase()}
              </span>
              <div>
                <h3>{team.name}</h3>
                <p>
                  {team.members.length}{' '}
                  {team.members.length === 1 ? 'member' : 'members'}
                </p>
              </div>
            </div>
            <p className="team-members">
              {team.members.map((member) => member.display_name).join(', ')}
            </p>
            <button
              className="button button-secondary button-small mt-4"
              onClick={() => {
                void (async () => {
                  try {
                    const invite = await createInvite(team.id)
                    const url = `${window.location.origin}/workspace?invite=${invite.token}`
                    setInviteUrl(url)
                    setInviteCopied(false)
                    setMessage(
                      'Single-use invite created; it expires in 24 hours.',
                    )
                  } catch (error) {
                    setMessage(
                      error instanceof Error
                        ? error.message
                        : 'Could not create the invite.',
                    )
                  }
                })()
              }}
              type="button"
            >
              Create invite
            </button>
          </li>
        ))}
      </ul>
      {inviteUrl && (
        <div className="invite-output panel">
          <div>
            <span>Single-use invitation</span>
            <output>{inviteUrl}</output>
          </div>
          <button
            className="button button-secondary button-small"
            onClick={() =>
              void navigator.clipboard.writeText(inviteUrl).then(
                () => {
                  setInviteCopied(true)
                  notify('Invitation link copied.')
                  window.setTimeout(() => setInviteCopied(false), 1800)
                },
                () => notify('Could not copy the invitation link.'),
              )
            }
            type="button"
          >
            {inviteCopied ? 'Copied! ✓' : 'Copy link'}
          </button>
        </div>
      )}
      <div className="section-heading">
        <div>
          <p className="eyebrow">Submissions</p>
          <h2>Projects</h2>
        </div>
        <span>{projectQuery.data?.length ?? 0} total</span>
      </div>
      {projectQuery.data?.length === 0 && (
        <EmptyState>No drafts or submissions yet.</EmptyState>
      )}
      <ul className="project-list">
        {projectQuery.data?.map((project) => (
          <li className="panel project-list-row" key={project.id}>
            <span className="project-list-title">
              <strong>{project.title}</strong>
              <small>{project.track_name}</small>
              <span
                className={`badge ${project.status === 'submitted' ? 'badge-green' : 'badge-amber'}`}
              >
                {project.status}
              </span>
            </span>
            <Link
              className="button button-secondary button-small"
              to={`/workspace/projects/${project.id}/edit`}
            >
              Edit project
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
