import { Link } from 'react-router'

import { useAuth } from './context'

export function AuthMenu() {
  const { user, isLoading, logout } = useAuth()

  if (isLoading)
    return <span className="text-sm text-slate-400">Checking session…</span>
  if (!user) {
    return (
      <Link className="text-sm text-cyan-300 hover:text-cyan-200" to="/login">
        Log in
      </Link>
    )
  }
  return (
    <div className="flex items-center gap-3 text-sm">
      <span>
        {user.display_name}{' '}
        <span className="text-slate-400">({user.role})</span>
      </span>
      <button
        className="rounded border border-slate-700 px-3 py-1 hover:bg-slate-800"
        onClick={() => void logout()}
        type="button"
      >
        Log out
      </button>
    </div>
  )
}
