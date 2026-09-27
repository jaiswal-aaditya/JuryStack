import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router'
import { z } from 'zod'

import { ApiError, events, ownedProject, saveProject, teams } from './api'
import { ErrorState, Loading } from '../../shared/AsyncState'

const schema = z.object({
  team_id: z.string().min(1, 'Choose a team.'),
  track_id: z.string().min(1, 'Choose a track.'),
  title: z.string().trim().min(1, 'Title is required.'),
  summary: z.string().trim().min(1, 'Summary is required.'),
  repo_url: z.union([z.literal(''), z.url('Enter a valid URL.')]),
})
type Fields = z.infer<typeof schema>

export function ProjectEditorPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const eventQuery = useQuery({ queryKey: ['events'], queryFn: events })
  const teamQuery = useQuery({ queryKey: ['teams'], queryFn: teams })
  const projectQuery = useQuery({
    queryKey: ['owned-project', projectId],
    queryFn: () => ownedProject(projectId ?? ''),
    enabled: Boolean(projectId),
  })
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [now] = useState(() => Date.now())
  const submitIntent = useRef(false)
  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<Fields>()

  useEffect(() => {
    if (projectQuery.data) {
      reset(projectQuery.data)
      // React Hook Form initialization follows the asynchronously loaded record.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAnswers(
        Object.fromEntries(
          projectQuery.data.custom_answers.map((item) => [
            item.question_id,
            item.answer,
          ]),
        ),
      )
    } else if (!projectId && teamQuery.data?.[0]) {
      reset({
        team_id: teamQuery.data[0].id,
        track_id: '',
        title: '',
        summary: '',
        repo_url: '',
      })
    }
  }, [projectId, projectQuery.data, reset, teamQuery.data])

  const teamId = useWatch({ control, name: 'team_id' })
  const team = teamQuery.data?.find((item) => item.id === teamId)
  const event = eventQuery.data?.find((item) => item.id === team?.event_id)
  const closed = event
    ? now >= new Date(event.submissions_close).getTime()
    : false
  const mutation = useMutation({
    mutationFn: (values: Fields) =>
      saveProject(
        {
          ...values,
          event_id: team?.event_id,
          custom_answers: Object.entries(answers).map(
            ([question_id, answer]) => ({ question_id, answer }),
          ),
          submit: submitIntent.current,
        },
        projectId,
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['my-projects'] })
      await navigate('/workspace')
    },
  })
  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values)
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        const name = issue.path[0]
        if (typeof name === 'string')
          setError(name as keyof Fields, { message: issue.message })
      }
      return
    }
    mutation.mutate(parsed.data)
  })
  const error = useMemo(() => {
    if (mutation.error instanceof ApiError && mutation.error.status === 403)
      return new Error('You are not allowed to edit this team’s project.')
    return mutation.error
  }, [mutation.error])

  if (eventQuery.isLoading || teamQuery.isLoading || projectQuery.isLoading)
    return <Loading label="Loading project form…" />
  if (eventQuery.error || teamQuery.error || projectQuery.error)
    return (
      <ErrorState
        error={eventQuery.error ?? teamQuery.error ?? projectQuery.error}
      />
    )
  return (
    <section className="max-w-2xl">
      <h1 className="text-3xl font-bold">
        {projectId ? 'Edit project' : 'Create a project'}
      </h1>
      {closed && (
        <div
          role="alert"
          className="mt-5 rounded border border-amber-700 bg-amber-950 p-4 text-amber-200"
        >
          The submission deadline has passed. This project is read-only.
        </div>
      )}
      {error && (
        <div className="mt-5">
          <ErrorState error={error} />
        </div>
      )}
      <form className="mt-8 space-y-5" onSubmit={submit}>
        <label className="block">
          Team
          <select
            className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            disabled={Boolean(projectId) || closed}
            {...register('team_id')}
          >
            <option value="">Choose a team</option>
            {teamQuery.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {errors.team_id && (
            <span className="text-sm text-red-300">
              {errors.team_id.message}
            </span>
          )}
        </label>
        <label className="block">
          Track
          <select
            className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            disabled={closed}
            {...register('track_id')}
          >
            <option value="">Choose a track</option>
            {event?.tracks.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {errors.track_id && (
            <span className="text-sm text-red-300">
              {errors.track_id.message}
            </span>
          )}
        </label>
        <label className="block">
          Title
          <input
            className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            disabled={closed}
            {...register('title')}
          />
          {errors.title && (
            <span className="text-sm text-red-300">{errors.title.message}</span>
          )}
        </label>
        <label className="block">
          Summary
          <textarea
            className="mt-2 min-h-28 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            disabled={closed}
            {...register('summary')}
          />
          {errors.summary && (
            <span className="text-sm text-red-300">
              {errors.summary.message}
            </span>
          )}
        </label>
        <label className="block">
          Repository URL
          <input
            className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            disabled={closed}
            type="url"
            {...register('repo_url')}
          />
          {errors.repo_url && (
            <span className="text-sm text-red-300">
              {errors.repo_url.message}
            </span>
          )}
        </label>
        {event?.custom_questions.map((question) => (
          <label className="block" key={question.id}>
            {question.prompt}
            {question.required && ' *'}
            <textarea
              className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              disabled={closed}
              onChange={(change) =>
                setAnswers((current) => ({
                  ...current,
                  [question.id]: change.target.value,
                }))
              }
              value={answers[question.id] ?? ''}
            />
          </label>
        ))}
        <div className="flex gap-3">
          <button
            className="rounded border border-cyan-500 px-4 py-2 text-cyan-300 disabled:opacity-50"
            disabled={closed || mutation.isPending}
            onClick={() => {
              submitIntent.current = false
            }}
            type="submit"
          >
            Save draft
          </button>
          <button
            className="rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
            disabled={closed || mutation.isPending}
            onClick={() => {
              submitIntent.current = true
            }}
            type="submit"
          >
            Submit project
          </button>
        </div>
      </form>
    </section>
  )
}
