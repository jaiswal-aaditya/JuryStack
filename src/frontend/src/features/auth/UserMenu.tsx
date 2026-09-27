import { Link, useNavigate } from 'react-router'

import { useAuth } from './context'
import { Avatar } from '../../shared/Avatar'

export function UserMenu() {
  const { user, isLoading, logout } = useAuth()
  const navigate = useNavigate()
  if (isLoading)
    return <span className="session-skeleton" aria-label="Checking session" />
  if (!user)
    return (
      <Link className="button button-primary button-small" to="/login">
        Log in
      </Link>
    )
  return (
    <details className="user-menu">
      <summary aria-label={`Open account menu for ${user.display_name}`}>
        <Avatar name={user.display_name} role={user.role} size="sm" />
        <span className="user-menu-name">{user.display_name}</span>
        <span aria-hidden="true" className="chevron">
          ⌄
        </span>
      </summary>
      <div className="user-popover">
        <div className="user-summary">
          <Avatar name={user.display_name} role={user.role} />
          <div>
            <strong>{user.display_name}</strong>
            <span>{user.email}</span>
            <span className="role-label">{user.role}</span>
          </div>
        </div>
        <div className="popover-divider" />
        <Link className="menu-action" to="/profile">
          Profile
        </Link>
        <div className="popover-divider" />
        <button
          className="menu-action menu-action-danger"
          onClick={() => void logout().then(() => navigate('/'))}
          type="button"
        >
          Log out
        </button>
      </div>
    </details>
  )
}
