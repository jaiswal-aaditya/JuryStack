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

export function ParticipantPage() {
  const queryClient = useQueryClient()
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
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-widest text-cyan-400">
            Participant
          </p>
          <h1 className="mt-2 text-3xl font-bold">Your teams and projects</h1>
        </div>
        {(teamQuery.data?.length ?? 0) > 0 && (
          <Link
            className="rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950"
            to="/workspace/projects/new"
          >
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
          className="rounded-xl border border-slate-800 bg-slate-900 p-5"
          onSubmit={(event) => {
            event.preventDefault()
            createTeamMutation.mutate({ eventId: chosenEvent, name: teamName })
          }}
        >
          <h2 className="text-xl font-semibold">Create a team</h2>
          <select
            aria-label="Event"
            className="mt-4 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            onChange={(event) => setEventId(event.target.value)}
            value={chosenEvent}
          >
            {eventQuery.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <input
            aria-label="Team name"
            className="mt-3 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            onChange={(event) => setTeamName(event.target.value)}
            placeholder="Team name"
            required
            value={teamName}
          />
          {createTeamMutation.error && (
            <ErrorState error={createTeamMutation.error} />
          )}
          <button
            className="mt-3 rounded border border-cyan-500 px-4 py-2 text-cyan-300"
            disabled={!chosenEvent || createTeamMutation.isPending}
          >
            Create team
          </button>
        </form>
        <form
          className="rounded-xl border border-slate-800 bg-slate-900 p-5"
          onSubmit={(event) => {
            event.preventDefault()
            acceptMutation.mutate()
          }}
        >
          <h2 className="text-xl font-semibold">Join with an invite</h2>
          <input
            aria-label="Invite token"
            className="mt-4 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            onChange={(event) => setToken(event.target.value)}
            placeholder="Paste invite token"
            required
            value={token}
          />
          {acceptMutation.error && <ErrorState error={acceptMutation.error} />}
          <button
            className="mt-3 rounded border border-cyan-500 px-4 py-2 text-cyan-300"
            disabled={acceptMutation.isPending}
          >
            Join team
          </button>
        </form>
      </div>
      <h2 className="mt-10 text-2xl font-semibold">Teams</h2>
      {teamQuery.data?.length === 0 && (
        <EmptyState>You do not belong to a team yet.</EmptyState>
      )}
      <ul className="mt-4 grid gap-4 md:grid-cols-2">
        {teamQuery.data?.map((team) => (
          <li className="rounded-xl border border-slate-800 p-5" key={team.id}>
            <h3 className="text-lg font-semibold">{team.name}</h3>
            <p className="mt-2 text-sm text-slate-400">
              {team.members.map((member) => member.display_name).join(', ')}
            </p>
            <button
              className="mt-4 text-sm text-cyan-300"
              onClick={() => {
                void (async () => {
                  try {
                    const invite = await createInvite(team.id)
                    const url = `${window.location.origin}/workspace?invite=${invite.token}`
                    setInviteUrl(url)
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
        <output className="mt-4 block break-all rounded bg-slate-900 p-3 text-sm text-cyan-200">
          {inviteUrl}
        </output>
      )}
      <h2 className="mt-10 text-2xl font-semibold">Projects</h2>
      {projectQuery.data?.length === 0 && (
        <EmptyState>No drafts or submissions yet.</EmptyState>
      )}
      <ul className="mt-4 space-y-3">
        {projectQuery.data?.map((project) => (
          <li
            className="flex items-center justify-between rounded border border-slate-800 p-4"
            key={project.id}
          >
            <span>
              {project.title}{' '}
              <span className="ml-2 text-sm text-slate-400">
                {project.status}
              </span>
            </span>
            <Link
              className="text-cyan-300"
              to={`/workspace/projects/${project.id}/edit`}
            >
              Edit
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
