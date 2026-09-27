import { z } from 'zod'

const userSchema = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  role: z.enum(['participant', 'judge', 'organizer', 'admin']),
})

const errorSchema = z.object({
  error: z.object({ message: z.string() }),
})

export type CurrentUser = z.infer<typeof userSchema>

async function errorMessage(response: Response): Promise<string> {
  const parsed = errorSchema.safeParse(await response.json().catch(() => null))
  return parsed.success ? parsed.data.error.message : 'The request failed.'
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await fetch('/api/auth/me', { credentials: 'same-origin' })
  if (response.status === 401) return null
  if (!response.ok) throw new Error(await errorMessage(response))
  return userSchema.parse(await response.json())
}

export async function login(input: {
  email: string
  password: string
}): Promise<CurrentUser> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return userSchema.parse(await response.json())
}

export async function logout(): Promise<void> {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
  })
  if (!response.ok) throw new Error(await errorMessage(response))
}
