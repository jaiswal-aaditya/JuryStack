import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'

import {
  saveScorecardDraft,
  scorecardWorkspace,
  submitScorecard,
  type ScorecardWorkspace,
} from './api'
import { ErrorState, Loading } from '../../shared/AsyncState'

function JudgeScorecardForm({
  projectId,
  workspace,
}: {
  projectId: string
  workspace: ScorecardWorkspace
}) {
  const queryClient = useQueryClient()
  const criteria = useMemo(() => {
    if (workspace.scorecard) return workspace.scorecard.criteria
    return workspace.rubric.criteria.map((criterion) => ({
      criterion_id: criterion.id,
      label: criterion.label,
      description: criterion.description,
      minimum_score: criterion.minimum_score,
      maximum_score: criterion.maximum_score,
      weight: criterion.weight,
      display_order: criterion.display_order,
      score: null,
    }))
  }, [workspace])
  const [scores, setScores] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      criteria.map((criterion) => [
        criterion.criterion_id,
        criterion.score === null ? '' : String(criterion.score),
      ]),
    ),
  )
  const [comment, setComment] = useState(workspace.scorecard?.comment ?? '')
  const [message, setMessage] = useState('')

  const draftMutation = useMutation({
    mutationFn: () =>
      saveScorecardDraft(projectId, {
        rubric_id: workspace.rubric.id,
        comment,
        scores: criteria
          .filter((criterion) => scores[criterion.criterion_id] !== '')
          .map((criterion) => ({
            criterion_id: criterion.criterion_id,
            score: Number(scores[criterion.criterion_id]),
          })),
      }),
    onSuccess: async () => {
      setMessage('Draft scorecard saved.')
      await queryClient.invalidateQueries({
        queryKey: ['judge-scorecard', projectId],
      })
    },
  })
  const submitMutation = useMutation({
    mutationFn: async () => {
      const saved = await draftMutation.mutateAsync()
      return submitScorecard(saved.id)
    },
    onSuccess: async () => {
      setMessage('Scorecard submitted and locked.')
      await queryClient.invalidateQueries({
        queryKey: ['judge-scorecard', projectId],
      })
    },
  })

  const submitted = workspace.scorecard?.status === 'submitted'
  const mutationError = draftMutation.error ?? submitMutation.error
  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <Link className="text-sm text-cyan-300" to="/judge/assignments">
          ← Assigned projects
        </Link>
        <p className="mt-5 text-sm uppercase tracking-widest text-cyan-400">
          {workspace.project.track_name} · Rubric version{' '}
          {workspace.rubric.version}
        </p>
        <h1 className="mt-2 text-3xl font-bold">{workspace.project.title}</h1>
        <p className="mt-3 text-slate-400">{workspace.project.summary}</p>
        <p className="mt-3 text-sm text-slate-400">
          {submitted
            ? 'Submitted scorecards are read-only.'
            : 'Save a partial draft at any time. Every criterion is required to submit.'}
        </p>
      </div>

      {message && (
        <p
          className="rounded border border-emerald-800 bg-emerald-950 p-3 text-emerald-200"
          role="status"
        >
          {message}
        </p>
      )}
      {mutationError && <ErrorState error={mutationError} />}

      <form
        className="space-y-5"
        onSubmit={(event) => {
          event.preventDefault()
          draftMutation.mutate()
        }}
      >
        {criteria.map((criterion) => (
          <fieldset
            className="rounded-xl border border-slate-800 bg-slate-900 p-5"
            disabled={submitted}
            key={criterion.criterion_id}
          >
            <label
              className="block font-semibold"
              htmlFor={`score-${criterion.criterion_id}`}
            >
              {criterion.label}
            </label>
            {criterion.description && (
              <p className="mt-1 text-sm text-slate-400">
                {criterion.description}
              </p>
            )}
            <p className="mt-1 text-xs text-slate-500">
              {criterion.minimum_score}–{criterion.maximum_score} · weight{' '}
              {criterion.weight}
            </p>
            <input
              className="mt-3 w-28 rounded border border-slate-700 bg-slate-950 px-3 py-2"
              id={`score-${criterion.criterion_id}`}
              max={criterion.maximum_score}
              min={criterion.minimum_score}
              onChange={(event) =>
                setScores((current) => ({
                  ...current,
                  [criterion.criterion_id]: event.target.value,
                }))
              }
              required={false}
              type="number"
              value={scores[criterion.criterion_id] ?? ''}
            />
          </fieldset>
        ))}

        <label className="block font-semibold" htmlFor="scorecard-comment">
          Private judge comment
        </label>
        <textarea
          className="min-h-32 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
          disabled={submitted}
          id="scorecard-comment"
          maxLength={10000}
          onChange={(event) => setComment(event.target.value)}
          value={comment}
        />

        {!submitted && (
          <div className="flex flex-wrap gap-3">
            <button
              className="rounded border border-cyan-500 px-4 py-2 text-cyan-300 disabled:opacity-50"
              disabled={draftMutation.isPending || submitMutation.isPending}
              type="submit"
            >
              Save draft
            </button>
            <button
              className="rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
              disabled={draftMutation.isPending || submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
              type="button"
            >
              Submit scorecard
            </button>
          </div>
        )}
      </form>
    </section>
  )
}

export function JudgeScorecardPage() {
  const { projectId = '' } = useParams()
  const query = useQuery({
    queryKey: ['judge-scorecard', projectId],
    queryFn: () => scorecardWorkspace(projectId),
    retry: false,
  })

  if (query.isLoading) return <Loading label="Loading your scorecard…" />
  if (query.error) return <ErrorState error={query.error} />
  if (!query.data) return null

  return (
    <JudgeScorecardForm
      key={projectId}
      projectId={projectId}
      workspace={query.data}
    />
  )
}
