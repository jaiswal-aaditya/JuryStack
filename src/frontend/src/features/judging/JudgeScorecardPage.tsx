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
import { ConfirmDialog } from '../../shared/ConfirmDialog'

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
  const [confirming, setConfirming] = useState(false)

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
  const completedCount = criteria.filter(
    (criterion) => scores[criterion.criterion_id] !== '',
  ).length
  const complete = completedCount === criteria.length
  const mutationError = draftMutation.error ?? submitMutation.error
  return (
    <section className="scorecard-page">
      <div className="scorecard-heading">
        <Link className="back-link" to="/judge/assignments">
          ← Assigned projects
        </Link>
        <div className="scorecard-title-row">
          <div>
            <p className="eyebrow">
              {workspace.project.track_name} · Rubric v
              {workspace.rubric.version}
            </p>
            <h1>{workspace.project.title}</h1>
            <p>{workspace.project.summary}</p>
          </div>
          <span
            className={`badge ${submitted ? 'badge-green' : 'badge-amber'}`}
          >
            {submitted
              ? 'Submitted · read-only'
              : workspace.scorecard
                ? 'Draft saved'
                : 'Not started'}
          </span>
        </div>
      </div>

      <div className="scorecard-progress panel">
        <div>
          <span>Evaluation progress</span>
          <strong>
            {completedCount} of {criteria.length} criteria scored
          </strong>
        </div>
        <div
          className="progress-track"
          aria-label={`${completedCount} of ${criteria.length} criteria scored`}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={criteria.length}
          aria-valuenow={completedCount}
        >
          <span
            style={{
              width: `${criteria.length ? (completedCount / criteria.length) * 100 : 0}%`,
            }}
          />
        </div>
        <p>
          {submitted
            ? 'This evaluation is final and cannot be changed.'
            : 'Save a partial draft at any time. Every criterion is required for final submission.'}
        </p>
      </div>

      {message && (
        <p className="alert alert-success" role="status">
          {message}
        </p>
      )}
      {mutationError && <ErrorState error={mutationError} />}

      <form
        className="scorecard-form"
        onSubmit={(event) => {
          event.preventDefault()
          draftMutation.mutate()
        }}
      >
        {criteria.map((criterion) => (
          <fieldset
            className="criterion-card"
            disabled={submitted}
            key={criterion.criterion_id}
          >
            <label
              className="criterion-label"
              htmlFor={`score-${criterion.criterion_id}`}
            >
              {criterion.label}
            </label>
            {criterion.description && (
              <p className="criterion-description">{criterion.description}</p>
            )}
            <div className="criterion-meta">
              <span>
                Score range {criterion.minimum_score}–{criterion.maximum_score}
              </span>
              <span>Weight {criterion.weight}</span>
            </div>
            <div className="score-input-wrap">
              <input
                className="score-input"
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
              <span>/ {criterion.maximum_score}</span>
            </div>
          </fieldset>
        ))}

        <div className="panel comment-panel">
          <label className="criterion-label" htmlFor="scorecard-comment">
            Private judge comment
          </label>
          <p className="criterion-description">
            Visible only through organizer-authorized review tools; never to
            peer judges.
          </p>
          <textarea
            disabled={submitted}
            id="scorecard-comment"
            maxLength={10000}
            onChange={(event) => setComment(event.target.value)}
            value={comment}
          />
        </div>

        {!submitted && (
          <div className="scorecard-actions">
            <button
              className="button button-secondary"
              disabled={draftMutation.isPending || submitMutation.isPending}
              type="submit"
            >
              Save draft
            </button>
            <button
              className="button button-primary"
              disabled={
                !complete || draftMutation.isPending || submitMutation.isPending
              }
              onClick={() => setConfirming(true)}
              type="button"
            >
              Submit scorecard
            </button>
          </div>
        )}
      </form>
      <ConfirmDialog
        open={confirming}
        title="Submit this evaluation?"
        description="All scores and comments will be saved, then this scorecard will be locked. This action cannot be undone."
        confirmLabel="Submit final evaluation"
        pending={submitMutation.isPending}
        onCancel={() => setConfirming(false)}
        onConfirm={() =>
          submitMutation.mutate(undefined, {
            onSuccess: () => setConfirming(false),
          })
        }
      />
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
