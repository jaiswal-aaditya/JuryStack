import { useState } from 'react'
import { NavLink, Outlet } from 'react-router'

import { useAuth } from './features/auth/context'
import { UserMenu } from './features/auth/UserMenu'
import { Brand } from './shared/Brand'
import { ThemeToggle } from './shared/ThemeToggle'
import './App.css'

interface NavigationItem {
  label: string
  to: string
  end?: boolean
}

function navigationFor(role?: string): NavigationItem[] {
  const items: NavigationItem[] = [{ label: 'Projects', to: '/', end: true }]
  if (!role) return items
  items.unshift({ label: 'Dashboard', to: '/dashboard', end: true })
  if (role === 'participant')
    items.push({ label: 'Workspace', to: '/workspace' })
  if (role === 'judge')
    items.push({ label: 'Assigned projects', to: '/judge/assignments' })
  if (role === 'organizer' || role === 'admin') {
    items.push(
      { label: 'Events', to: '/organizer/events' },
      { label: 'Judging', to: '/organizer/judging' },
      { label: 'Operations', to: '/organizer/operations' },
    )
  }
  return items
}

function NavigationLinks({
  items,
  onNavigate,
}: {
  items: NavigationItem[]
  onNavigate?: () => void
}) {
  return (
    <>
      {items.map((item) => (
        <NavLink
          className={({ isActive }) =>
            `nav-link ${isActive ? 'nav-link-active' : ''}`
          }
          end={item.end}
          key={item.to}
          onClick={onNavigate}
          to={item.to}
        >
          {item.label}
        </NavLink>
      ))}
    </>
  )
}

export function App() {
  const { user } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const items = navigationFor(user?.role)
  return (
    <div className="app-shell">
      <header className="site-header">
        <nav aria-label="Primary" className="header-inner">
          <Brand />
          <div className="desktop-nav">
            <NavigationLinks items={items} />
          </div>
          <div className="header-actions">
            <div className="header-theme">
              <ThemeToggle compact />
            </div>
            <UserMenu />
            <button
              aria-expanded={mobileOpen}
              aria-label="Toggle navigation"
              className="mobile-menu-button"
              onClick={() => setMobileOpen((open) => !open)}
              type="button"
            >
              <span />
              <span />
              <span />
            </button>
          </div>
        </nav>
        {mobileOpen && (
          <div className="mobile-nav" aria-label="Mobile navigation">
            <NavigationLinks
              items={items}
              onNavigate={() => setMobileOpen(false)}
            />
          </div>
        )}
      </header>
      <main className="page-container">
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="footer-brand">
          <Brand linked={false} />
          <p>
            JuryStack is a modern, open-source, self-hostable hackathon
            submission and judging platform that manages the entire event
            lifecycle—from teams and submissions to judging, normalization,
            results, and export.
          </p>
        </div>
        <span className="footer-badge">Open Source &amp; Self-Hostable</span>
      </footer>
    </div>
  )
}
