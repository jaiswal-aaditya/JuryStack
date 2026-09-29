import { useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router'

import { useAuth } from './context'
import { Avatar } from '../../shared/Avatar'

export function UserMenu() {
  const { user, isLoading, logout } = useAuth()
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDetailsElement>(null)

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      const menu = menuRef.current
      if (menu?.open && !menu.contains(event.target as Node)) menu.open = false
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      const menu = menuRef.current
      if (event.key !== 'Escape' || !menu?.open) return
      menu.open = false
      menu.querySelector('summary')?.focus()
    }

    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  if (isLoading)
    return <span className="session-skeleton" aria-label="Checking session" />
  if (!user)
    return (
      <Link className="button button-primary button-small" to="/login">
        Log in
      </Link>
    )
  return (
    <details className="user-menu" ref={menuRef}>
      <summary aria-label={`Open account menu for ${user.display_name}`}>
        <Avatar name={user.display_name} role={user.role} size="sm" />
        <span className="user-menu-name">{user.display_name}</span>
        <span aria-hidden="true" className="chevron">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="m4 6 4 4 4-4" />
          </svg>
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
        <Link
          className="menu-action"
          onClick={() => {
            if (menuRef.current) menuRef.current.open = false
          }}
          to="/profile"
        >
          Profile
        </Link>
        <div className="popover-divider" />
        <button
          className="menu-action menu-action-danger"
          onClick={() => {
            if (menuRef.current) menuRef.current.open = false
            void logout().then(() => navigate('/'))
          }}
          type="button"
        >
          Log out
        </button>
      </div>
    </details>
  )
}
