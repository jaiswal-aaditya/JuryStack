import { z } from 'zod'

const ballotEntrySchema = z.object({
  project_id: z.string(),
  title: z.string(),
  summary: z.string(),
  track_name: z.string(),
  position: z.number(),
})
const ballotSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  entries: z.array(ballotEntrySchema),
  has_voted: z.boolean(),
})
const voteSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  cast_at: z.string(),
})
const votingWindowSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  opens_at: z.string(),
  closes_at: z.string(),
  is_enabled: z.boolean(),
})
const voterInvitationSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  email: z.string(),
  expires_at: z.string(),
  invitation_url: z.string().nullable(),
})

export type Ballot = z.infer<typeof ballotSchema>
export type BallotEntry = z.infer<typeof ballotEntrySchema>
export type VotingWindow = z.infer<typeof votingWindowSchema>

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

export async function fetchBallot(token: string) {
  return ballotSchema.parse(
    await request(`/api/voting/${encodeURIComponent(token)}/ballot`),
  )
}

export async function castVote(token: string, projectId: string) {
  return voteSchema.parse(
    await request(`/api/voting/${encodeURIComponent(token)}/vote`, {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    }),
  )
}

export async function upsertVotingWindow(
  eventId: string,
  input: { opens_at: string; closes_at: string; is_enabled: boolean },
) {
  return votingWindowSchema.parse(
    await request(`/api/events/${encodeURIComponent(eventId)}/voting-window`, {
      method: 'PUT',
      body: JSON.stringify(input),
    }),
  )
}

export async function createVoterInvitation(
  eventId: string,
  input: { email: string; expires_in_hours: number },
) {
  return voterInvitationSchema.parse(
    await request(
      `/api/events/${encodeURIComponent(eventId)}/voter-invitations`,
      { method: 'POST', body: JSON.stringify(input) },
    ),
  )
}