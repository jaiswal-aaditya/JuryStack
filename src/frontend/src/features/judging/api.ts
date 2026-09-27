import { z } from 'zod'

const criterionSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  minimum_score: z.number(),
  maximum_score: z.number(),
  weight: z.number(),
  display_order: z.number(),
})
const rubricSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  version: z.number(),
  is_active: z.boolean(),
  criteria: z.array(criterionSchema),
})
const invitationSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  email: z.string(),
  track_ids: z.array(z.string()),
  expires_at: z.string(),
  accepted_by_user_id: z.string().nullable(),
  invitation_url: z.string().nullable(),
})
const invitationPreviewSchema = z.object({
  event_id: z.string(),
  event_name: z.string(),
  email: z.string(),
  track_names: z.array(z.string()),
  expires_at: z.string(),
})
const judgeSchema = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  track_ids: z.array(z.string()),
})
const assignmentSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  judge_id: z.string(),
  judge_name: z.string(),
  project_id: z.string(),
  project_title: z.string(),
  track_id: z.string(),
  track_name: z.string(),
})
const judgeProjectSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  title: z.string(),
  summary: z.string(),
  repo_url: z.string(),
  track_id: z.string(),
  track_name: z.string(),
  submitted_at: z.string().nullable(),
})
const scoreCriterionSchema = z.object({
  criterion_id: z.string(),
  label: z.string(),
  description: z.string(),
  minimum_score: z.number(),
  maximum_score: z.number(),
  weight: z.number(),
  display_order: z.number(),
  score: z.number().nullable(),
})
const scorecardSchema = z.object({
  id: z.string(),
  judge_id: z.string(),
  project_id: z.string(),
  project_title: z.string(),
  event_id: z.string(),
  track_id: z.string(),
  track_name: z.string(),
  rubric_id: z.string(),
  rubric_version: z.number(),
  status: z.string(),
  comment: z.string(),
  submitted_at: z.string().nullable(),
  criteria: z.array(scoreCriterionSchema),
})
const scorecardWorkspaceSchema = z.object({
  project: judgeProjectSchema,
  rubric: rubricSchema,
  scorecard: scorecardSchema.nullable(),
})

export type Rubric = z.infer<typeof rubricSchema>
export type Judge = z.infer<typeof judgeSchema>
export type Assignment = z.infer<typeof assignmentSchema>
export type Scorecard = z.infer<typeof scorecardSchema>
export type ScorecardWorkspace = z.infer<typeof scorecardWorkspaceSchema>

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
      .object({ error: z.object({ message: z.string() }) })
      .safeParse(body)
    throw new Error(
      parsed.success ? parsed.data.error.message : 'The request failed.',
    )
  }
  return body
}

export async function rubrics(eventId: string) {
  return z
    .array(rubricSchema)
    .parse(await request(`/api/events/${eventId}/rubrics`))
}

export async function createRubric(
  eventId: string,
  criteria: Array<{
    label: string
    description: string
    minimum_score: number
    maximum_score: number
    weight: number
    display_order: number
  }>,
) {
  return rubricSchema.parse(
    await request(`/api/events/${eventId}/rubrics`, {
      method: 'POST',
      body: JSON.stringify({ criteria }),
    }),
  )
}

export async function invitations(eventId: string) {
  return z
    .array(invitationSchema)
    .parse(await request(`/api/events/${eventId}/judge-invitations`))
}

export async function createInvitation(input: {
  event_id: string
  email: string
  track_ids: string[]
  expires_in_hours: number
}) {
  return invitationSchema.parse(
    await request('/api/judge-invitations', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  )
}

export async function invitationPreview(token: string) {
  return invitationPreviewSchema.parse(
    await request(`/api/judge-invitations/${encodeURIComponent(token)}`),
  )
}

export async function acceptJudgeInvitation(
  token: string,
  input: { display_name?: string; password?: string },
) {
  return judgeSchema.parse(
    await request(
      `/api/judge-invitations/${encodeURIComponent(token)}/accept`,
      { method: 'POST', body: JSON.stringify(input) },
    ),
  )
}

export async function judges(eventId: string) {
  return z
    .array(judgeSchema)
    .parse(await request(`/api/events/${eventId}/judges`))
}

export async function assignments(eventId: string) {
  return z
    .array(assignmentSchema)
    .parse(await request(`/api/events/${eventId}/judge-assignments`))
}

export async function createAssignment(judgeId: string, projectId: string) {
  return assignmentSchema.parse(
    await request('/api/judge-assignments', {
      method: 'POST',
      body: JSON.stringify({ judge_id: judgeId, project_id: projectId }),
    }),
  )
}

export async function deleteAssignment(id: string) {
  await request(`/api/judge-assignments/${id}`, { method: 'DELETE' })
}

export async function balanceAssignments(
  eventId: string,
  reviewsPerProject: number,
) {
  return z
    .object({ created: z.array(assignmentSchema), created_count: z.number() })
    .parse(
      await request(`/api/events/${eventId}/judge-assignments/balance`, {
        method: 'POST',
        body: JSON.stringify({ reviews_per_project: reviewsPerProject }),
      }),
    )
}

export async function judgeProjects() {
  return z.array(judgeProjectSchema).parse(await request('/api/judge/projects'))
}

export async function scorecardWorkspace(projectId: string) {
  return scorecardWorkspaceSchema.parse(
    await request(
      `/api/judge/projects/${encodeURIComponent(projectId)}/scorecard`,
    ),
  )
}

export async function saveScorecardDraft(
  projectId: string,
  input: {
    rubric_id: string
    comment: string
    scores: Array<{ criterion_id: string; score: number }>
  },
) {
  return scorecardSchema.parse(
    await request(
      `/api/judge/projects/${encodeURIComponent(projectId)}/scorecard`,
      {
        method: 'PUT',
        body: JSON.stringify(input),
      },
    ),
  )
}

export async function submitScorecard(scorecardId: string) {
  return scorecardSchema.parse(
    await request(
      `/api/judge/scorecards/${encodeURIComponent(scorecardId)}/submit`,
      { method: 'POST' },
    ),
  )
}
