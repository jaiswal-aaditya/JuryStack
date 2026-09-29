import { Link } from 'react-router'

import { useAuth } from './context'
import { Avatar } from '../../shared/Avatar'
import { ThemeToggle } from '../../shared/ThemeToggle'

export function ProfilePage() {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user)
    return (
      <section className="narrow-page empty-state">
        <h1>Sign in to view your profile</h1>
        <Link className="button button-primary" to="/login">
          Log in
        </Link>
      </section>
    )
  return (
    <section className="narrow-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Profile</h1>
          <p>Your account details and display preferences.</p>
        </div>
      </div>
      <div className="panel profile-card">
        <div className="profile-identity">
          <Avatar name={user.display_name} role={user.role} size="lg" />
          <div>
            <h2>{user.display_name}</h2>
            <span className="badge badge-blue">{user.role}</span>
          </div>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Display name</dt>
            <dd>{user.display_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd className="capitalize">{user.role}</dd>
          </div>
        </dl>
        <p className="helper-text">
          Account details are managed by the local event organizer and are
          read-only here.
        </p>
      </div>
      <div className="panel profile-preferences">
        <div>
          <h2>Appearance</h2>
          <p className="helper-text">
            Choose a light or dark theme for this browser.
          </p>
        </div>
        <ThemeToggle />
      </div>
    </section>
  )
}
