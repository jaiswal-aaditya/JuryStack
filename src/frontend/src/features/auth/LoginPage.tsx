import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { z } from 'zod'

import { useAuth } from './context'

const loginSchema = z.object({
  email: z.string().trim().email('Enter a valid email address.'),
  password: z.string().min(8, 'Password must contain at least 8 characters.'),
})
type LoginFields = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [requestError, setRequestError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFields>()

  const submit = handleSubmit(async (values) => {
    setRequestError(null)
    const parsed = loginSchema.safeParse(values)
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        const field = issue.path[0]
        if (field === 'email' || field === 'password') {
          setError(field, { message: issue.message })
        }
      }
      return
    }
    try {
      await login(parsed.data)
      await navigate('/')
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : 'Login failed.')
    }
  })

  return (
    <section className="mx-auto max-w-md" aria-labelledby="login-title">
      <h1 id="login-title" className="text-3xl font-semibold">
        Log in to JuryStack
      </h1>
      <form className="mt-8 space-y-5" noValidate onSubmit={submit}>
        <div>
          <label className="block text-sm font-medium" htmlFor="email">
            Email
          </label>
          <input
            className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            id="email"
            type="email"
            autoComplete="email"
            {...register('email')}
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-300">{errors.email.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium" htmlFor="password">
            Password
          </label>
          <input
            className="mt-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            id="password"
            type="password"
            autoComplete="current-password"
            {...register('password')}
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-300">
              {errors.password.message}
            </p>
          )}
        </div>
        {requestError && (
          <p role="alert" className="text-sm text-red-300">
            {requestError}
          </p>
        )}
        <button
          className="w-full rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
    </section>
  )
}
