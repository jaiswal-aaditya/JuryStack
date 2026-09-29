import { z } from 'zod'

const answerSchema = z.object({ question_id: z.string(), answer: z.string() })
const projectSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  team_id: z.string(),
  team_name: z.string(),
  track_id: z.string(),
  track_name: z.string(),
  title: z.string(),
  summary: z.string(),
  repo_url: z.string(),
  status: z.string(),
  submitted_at: z.string().nullable(),
  custom_answers: z.array(answerSchema),
})
const trackSchema = z.object({ id: z.string(), name: z.string() })
const eventSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  starts_at: z.string().nullable(),
  submissions_open: z.string().nullable(),
  submissions_close: z.string(),
  tracks: z.array(trackSchema),
  prizes: z.array(
    z.object({ id: z.string(), name: z.string(), description: z.string() }),
  ),
  custom_questions: z.array(
    z.object({
      id: z.string(),
      prompt: z.string(),
      position: z.number(),
      required: z.boolean(),
    }),
  ),
})
const teamSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  name: z.string(),
  members: z.array(
    z.object({
      id: z.string(),
      email: z.string(),
      display_name: z.string(),
    }),
  ),
})

export type Project = z.infer<typeof projectSchema>
export type Event = z.infer<typeof eventSchema>
export type Team = z.infer<typeof teamSchema>

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(message: string, status: number, code: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...init,
    headers: init?.body
      ? { 'Content-Type': 'application/json', ...init.headers }
      : init?.headers,
  })
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const parsed = z
      .object({ error: z.object({ code: z.string(), message: z.string() }) })
      .safeParse(body)
    throw new ApiError(
      parsed.success ? parsed.data.error.message : 'The request failed.',
      response.status,
      parsed.success ? parsed.data.error.code : 'request_failed',
    )
  }
  return body
}

export async function gallery(
  search = '',
  trackId = '',
  limit = 100,
  offset = 0,
) {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (trackId) params.set('track_id', trackId)
  params.set('limit', String(limit))
  params.set('offset', String(offset))
  const suffix = params.size ? `?${params.toString()}` : ''
  return z
    .object({ items: z.array(projectSchema), total: z.number() })
    .parse(await request(`/api/public/projects${suffix}`))
}

export async function publicProject(id: string) {
  return projectSchema.parse(await request(`/api/public/projects/${id}`))
}

export async function events() {
  return z.array(eventSchema).parse(await request('/api/events'))
}

export async function saveEvent(payload: Record<string, unknown>, id?: string) {
  return eventSchema.parse(
    await request(id ? `/api/events/${id}` : '/api/events', {
      method: id ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    }),
  )
}

export async function teams() {
  return z.array(teamSchema).parse(await request('/api/teams'))
}

export async function createTeam(eventId: string, name: string) {
  return teamSchema.parse(
    await request('/api/teams', {
      method: 'POST',
      body: JSON.stringify({ event_id: eventId, name }),
    }),
  )
}

export async function createInvite(teamId: string) {
  return z.object({ token: z.string(), expires_at: z.string() }).parse(
    await request(`/api/teams/${teamId}/invites`, {
      method: 'POST',
      body: JSON.stringify({ expires_in_hours: 24 }),
    }),
  )
}

export async function acceptInvite(token: string) {
  return teamSchema.parse(
    await request(`/api/team-invites/${encodeURIComponent(token)}/accept`, {
      method: 'POST',
    }),
  )
}

export async function myProjects() {
  return z.array(projectSchema).parse(await request('/api/projects'))
}

export async function ownedProject(id: string) {
  return projectSchema.parse(await request(`/api/projects/${id}`))
}

export interface ProjectPayload {
  event_id?: string
  team_id?: string
  track_id?: string
  title: string
  summary: string
  repo_url: string
  custom_answers: { question_id: string; answer: string }[]
  submit: boolean
}

export async function saveProject(payload: ProjectPayload, id?: string) {
  return projectSchema.parse(
    await request(id ? `/api/projects/${id}` : '/api/projects', {
      method: id ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    }),
  )
}
