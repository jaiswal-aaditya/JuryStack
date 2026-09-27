import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { z } from 'zod'

import { useAuth } from './context'
import { Brand } from '../../shared/Brand'

const loginSchema = z.object({
  email: z.string().trim().email('Enter a valid email address.'),
  password: z.string().min(8, 'Password must contain at least 8 characters.'),
})
type LoginFields = z.infer<typeof loginSchema>

function EyeIcon({ hidden }: { hidden: boolean }) {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 24 24">
      <path
        d="M3 12s3.25-5 9-5 9 5 9 5-3.25 5-9 5-9-5-9-5Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <circle
        cx="12"
        cy="12"
        r="2.25"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      {hidden && (
        <path
          d="m4 4 16 16"
          stroke="currentColor"
          strokeLinecap="round"
          strokeWidth="1.7"
        />
      )}
    </svg>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [requestError, setRequestError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)
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
      await navigate('/dashboard')
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : 'Login failed.')
    }
  })

  return (
    <section className="auth-page" aria-labelledby="login-title">
      <div className="auth-intro">
        <Brand linked={false} large />
        <p>
          A modern, open-source, self-hostable platform for the complete
          hackathon submission and judging lifecycle.
        </p>
        <ul aria-label="JuryStack benefits">
          <li>
            <span>✓</span> Focused judging workflows
          </li>
          <li>
            <span>✓</span> Private, role-scoped access
          </li>
          <li>
            <span>✓</span> Fully self-hosted
          </li>
        </ul>
      </div>
      <div className="auth-card">
        <div className="auth-card-brand">
          <Brand linked={false} />
        </div>
        <p className="auth-platform-copy">
          Manage teams, submissions, judging, and results in one focused local
          workspace.
        </p>
        <p className="eyebrow">Welcome back</p>
        <h1 id="login-title">Log in to your account</h1>
        <p className="auth-subtitle">
          Use the local credentials provided by your event organizer.
        </p>
        <form className="auth-form" noValidate onSubmit={submit}>
          <div className="field-group">
            <label className="field-label" htmlFor="email">
              Email
            </label>
            <input
              className="input"
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.org"
              aria-invalid={Boolean(errors.email)}
              {...register('email')}
            />
            {errors.email && (
              <p className="field-error">{errors.email.message}</p>
            )}
          </div>
          <div className="field-group">
            <label className="field-label" htmlFor="password">
              Password
            </label>
            <div className="password-field">
              <input
                className="input"
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                aria-invalid={Boolean(errors.password)}
                {...register('password')}
              />
              <button
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                className="password-toggle"
                onClick={() => setShowPassword((visible) => !visible)}
                type="button"
              >
                <EyeIcon hidden={showPassword} />
              </button>
            </div>
            {errors.password && (
              <p className="field-error">{errors.password.message}</p>
            )}
          </div>
          {requestError && (
            <p role="alert" className="alert alert-error">
              {requestError}
            </p>
          )}
          <button
            className="button button-primary button-full"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <p className="auth-note">
          New judge accounts are created through secure invitation links. Public
          signup is disabled to protect event roles.
        </p>
      </div>
    </section>
  )
}
