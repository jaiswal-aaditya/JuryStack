import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router'

import { castVote, fetchBallot } from './api'
import { ErrorState, Loading } from '../../shared/AsyncState'
import { Brand } from '../../shared/Brand'

export function VotingPage() {
  const { token = '' } = useParams()
  const queryClient = useQueryClient()
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null,
  )
  const query = useQuery({
    queryKey: ['voting-ballot', token],
    queryFn: () => fetchBallot(token),
    retry: false,
  })
  const mutation = useMutation({
    mutationFn: (projectId: string) => castVote(token, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voting-ballot', token] })
    },
  })

  if (query.isLoading) return <Loading label="Loading your ballot..." />
  if (query.error) return <ErrorState error={query.error} />
  const ballot = query.data
  if (!ballot) return null

  const hasVoted = ballot.has_voted || mutation.isSuccess

  if (hasVoted) {
    return (
      <section className="mx-auto max-w-xl panel p-7">
        <Brand linked={false} />
        <h1 className="mt-2 text-2xl font-bold">Thanks for voting</h1>
        <p className="mt-3 text-slate-300">
          Your vote has been recorded. Results become available once the
          voting window closes.
        </p>
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-2xl panel p-7">
      <Brand linked={false} />
      <p className="text-sm uppercase tracking-widest text-cyan-400">
        Community voting
      </p>
      <h1 className="mt-2 text-2xl font-bold">Pick your favorite project</h1>
      <p className="mt-3 text-slate-400">
        Projects are shown in a random order unique to your ballot. You may
        cast one vote.
      </p>
      {mutation.error && (
        <div className="mt-4">
          <ErrorState error={mutation.error} />
        </div>
      )}
      <div className="mt-5 grid gap-3">
        {ballot.entries.map((entry) => {
          const selected = selectedProjectId === entry.project_id
          return (
            <button
              className={`rounded-lg border p-4 text-left transition ${
                selected
                  ? 'border-cyan-400 bg-cyan-950/40'
                  : 'border-slate-700 hover:border-slate-500'
              }`}
              key={entry.project_id}
              onClick={() => setSelectedProjectId(entry.project_id)}
              type="button"
            >
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {entry.track_name}
              </p>
              <p className="mt-1 font-semibold">{entry.title}</p>
              <p className="mt-1 text-sm text-slate-400">{entry.summary}</p>
            </button>
          )
        })}
      </div>
      <button
        className="mt-6 w-full rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
        disabled={!selectedProjectId || mutation.isPending}
        onClick={() => selectedProjectId && mutation.mutate(selectedProjectId)}
        type="button"
      >
        {mutation.isPending ? 'Submitting...' : 'Cast vote'}
      </button>
    </section>
  )
}