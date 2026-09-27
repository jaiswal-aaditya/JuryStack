import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { acceptJudgeInvitation, invitationPreview } from './api'
import { useAuth } from '../auth/context'
import { ErrorState, Loading } from '../../shared/AsyncState'
import { Brand } from '../../shared/Brand'

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

export function JudgeInvitationPage() {
  const { token = '' } = useParams()
  const auth = useAuth()
  const query = useQuery({
    queryKey: ['judge-invitation', token],
    queryFn: () => invitationPreview(token),
    retry: false,
  })
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const mutation = useMutation({
    mutationFn: () =>
      acceptJudgeInvitation(
        token,
        auth.user ? {} : { display_name: displayName, password },
      ),
  })
  if (query.isLoading) return <Loading label="Checking invitation…" />
  if (query.error) return <ErrorState error={query.error} />
  if (mutation.data) {
    return (
      <section className="mx-auto max-w-xl rounded-xl border border-emerald-800 bg-emerald-950 p-7">
        <h1 className="text-2xl font-bold">Invitation accepted</h1>
        <p className="mt-3">
          {mutation.data.display_name} can now sign in and view eligible
          assignments.
        </p>
        <Link
          className="mt-5 inline-block text-cyan-300"
          to={auth.user ? '/judge/assignments' : '/login'}
        >
          {auth.user ? 'Open judge workspace' : 'Sign in as the new judge'}
        </Link>
      </section>
    )
  }
  const existingAccount = auth.user?.email === query.data?.email
  return (
    <section className="mx-auto max-w-xl panel p-7">
      <Brand linked={false} />
      <p className="text-sm uppercase tracking-widest text-cyan-400">
        Local invitation
      </p>
      <h1 className="mt-2 text-2xl font-bold">
        Judge {query.data?.event_name}
      </h1>
      <p className="mt-3 text-slate-300">Invited email: {query.data?.email}</p>
      <p className="mt-1 text-slate-400">
        Tracks: {query.data?.track_names.join(', ')}
      </p>
      {auth.user && !existingAccount && (
        <div className="mt-5">
          <ErrorState
            error={
              new Error(
                'Sign out and use the invited email account to accept this link.',
              )
            }
          />
        </div>
      )}
      {!auth.user && (
        <div className="mt-5 space-y-3">
          <p className="text-sm text-slate-400">
            Create a local judge account. No email service or external account
            is used.
          </p>
          <label className="block">
            <span className="field-label">Display name</span>
            <input
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Display name"
              required
              value={displayName}
            />
          </label>
          <label className="block">
            <span className="field-label">Password</span>
            <div className="password-field">
              <input
                minLength={12}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Password (12+ characters)"
                required
                type={showPassword ? 'text' : 'password'}
                value={password}
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
          </label>
        </div>
      )}
      {mutation.error && (
        <div className="mt-4">
          <ErrorState error={mutation.error} />
        </div>
      )}
      <button
        className="mt-5 rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
        disabled={
          mutation.isPending ||
          Boolean(auth.user && !existingAccount) ||
          (!auth.user && (displayName.length === 0 || password.length < 12))
        }
        onClick={() => mutation.mutate()}
        type="button"
      >
        Accept invitation
      </button>
      {!auth.user && (
        <p className="mt-4 text-sm text-slate-400">
          Already registered?{' '}
          <Link className="text-cyan-300" to="/login">
            Sign in first
          </Link>
          , then reopen this link.
        </p>
      )}
    </section>
  )
}
