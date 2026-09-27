import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { events, saveEvent, type Event } from './api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'

interface FormState {
  name: string
  slug: string
  starts_at: string
  submissions_open: string
  submissions_close: string
  tracks: string
  prizes: string
  questions: string
}
const empty: FormState = {
  name: '',
  slug: '',
  starts_at: '',
  submissions_open: '',
  submissions_close: '',
  tracks: '',
  prizes: '',
  questions: '',
}

function localDate(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return shifted.toISOString().slice(0, 16)
}

function fromEvent(event: Event): FormState {
  return {
    name: event.name,
    slug: event.slug,
    starts_at: localDate(event.starts_at),
    submissions_open: localDate(event.submissions_open),
    submissions_close: localDate(event.submissions_close),
    tracks: event.tracks.map((item) => item.name).join('\n'),
    prizes: event.prizes
      .map((item) => `${item.name}|${item.description}`)
      .join('\n'),
    questions: event.custom_questions
      .map((item) => `${item.required ? '*' : ''}${item.prompt}`)
      .join('\n'),
  }
}

function lines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function OrganizerEventsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['events'], queryFn: events })
  const [selected, setSelected] = useState<string>()
  const [form, setForm] = useState<FormState>(empty)
  const [message, setMessage] = useState('')
  const mutation = useMutation({
    mutationFn: () =>
      saveEvent(
        {
          name: form.name,
          slug: form.slug,
          starts_at: form.starts_at
            ? new Date(form.starts_at).toISOString()
            : null,
          submissions_open: form.submissions_open
            ? new Date(form.submissions_open).toISOString()
            : null,
          submissions_close: new Date(form.submissions_close).toISOString(),
          tracks: lines(form.tracks).map((name, index) => ({
            id: selected
              ? query.data?.find((item) => item.id === selected)?.tracks[index]
                  ?.id
              : undefined,
            name,
          })),
          prizes: lines(form.prizes).map((line, index) => {
            const [name, description = ''] = line.split('|')
            return {
              id: selected
                ? query.data?.find((item) => item.id === selected)?.prizes[
                    index
                  ]?.id
                : undefined,
              name,
              description,
            }
          }),
          custom_questions: lines(form.questions).map((line, index) => ({
            id: selected
              ? query.data?.find((item) => item.id === selected)
                  ?.custom_questions[index]?.id
              : undefined,
            prompt: line.replace(/^\*/, ''),
            required: line.startsWith('*'),
          })),
        },
        selected,
      ),
    onSuccess: async (saved) => {
      setSelected(saved.id)
      setForm(fromEvent(saved))
      setMessage('Event configuration saved in UTC.')
      await queryClient.invalidateQueries({ queryKey: ['events'] })
    },
  })
  const update = (key: keyof FormState, value: string) =>
    setForm((current) => ({ ...current, [key]: value }))
  if (query.isLoading) return <Loading label="Loading events…" />
  if (query.error) return <ErrorState error={query.error} />
  return (
    <section>
      <p className="text-sm uppercase tracking-widest text-cyan-400">
        Organizer
      </p>
      <h1 className="mt-2 text-3xl font-bold">Event configuration</h1>
      <div className="mt-8 grid gap-8 lg:grid-cols-[18rem_1fr]">
        <aside>
          <button
            className="w-full rounded border border-cyan-500 px-4 py-2 text-cyan-300"
            onClick={() => {
              setSelected(undefined)
              setForm(empty)
              setMessage('')
            }}
            type="button"
          >
            New event
          </button>
          {query.data?.length === 0 && (
            <div className="mt-4">
              <EmptyState>No events have been created.</EmptyState>
            </div>
          )}
          <ul className="mt-4 space-y-2">
            {query.data?.map((event) => (
              <li key={event.id}>
                <button
                  className="w-full rounded border border-slate-800 p-3 text-left hover:bg-slate-900"
                  onClick={() => {
                    setSelected(event.id)
                    setForm(fromEvent(event))
                    setMessage('')
                  }}
                  type="button"
                >
                  {event.name}
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <form
          className="space-y-5 rounded-xl border border-slate-800 bg-slate-900 p-6"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate()
          }}
        >
          <h2 className="text-xl font-semibold">
            {selected ? 'Edit event' : 'Create event'}
          </h2>
          {message && (
            <p role="status" className="text-emerald-300">
              {message}
            </p>
          )}
          {mutation.error && <ErrorState error={mutation.error} />}
          <label className="block">
            Name
            <input
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              onChange={(event) => update('name', event.target.value)}
              required
              value={form.name}
            />
          </label>
          <label className="block">
            Slug
            <input
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              onChange={(event) => update('slug', event.target.value)}
              pattern="[a-z0-9]+(-[a-z0-9]+)*"
              required
              value={form.slug}
            />
          </label>
          <div className="grid gap-4 md:grid-cols-3">
            <label>
              Event starts
              <input
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                onChange={(event) => update('starts_at', event.target.value)}
                type="datetime-local"
                value={form.starts_at}
              />
            </label>
            <label>
              Submissions open
              <input
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                onChange={(event) =>
                  update('submissions_open', event.target.value)
                }
                type="datetime-local"
                value={form.submissions_open}
              />
            </label>
            <label>
              Submissions close
              <input
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                onChange={(event) =>
                  update('submissions_close', event.target.value)
                }
                required
                type="datetime-local"
                value={form.submissions_close}
              />
            </label>
          </div>
          <p className="text-sm text-slate-400">
            Dates are converted to UTC and enforced by the server.
          </p>
          <label className="block">
            Tracks <span className="text-slate-400">(one per line)</span>
            <textarea
              className="mt-2 min-h-28 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              onChange={(event) => update('tracks', event.target.value)}
              required
              value={form.tracks}
            />
          </label>
          <label className="block">
            Prizes <span className="text-slate-400">(name|description)</span>
            <textarea
              className="mt-2 min-h-24 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              onChange={(event) => update('prizes', event.target.value)}
              value={form.prizes}
            />
          </label>
          <label className="block">
            Submission questions{' '}
            <span className="text-slate-400">
              (prefix required questions with *)
            </span>
            <textarea
              className="mt-2 min-h-24 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              onChange={(event) => update('questions', event.target.value)}
              value={form.questions}
            />
          </label>
          <button
            className="rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
            disabled={mutation.isPending}
          >
            Save configuration
          </button>
        </form>
      </div>
    </section>
  )
}
