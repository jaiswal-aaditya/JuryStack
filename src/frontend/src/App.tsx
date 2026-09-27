import { Link, NavLink, Outlet } from 'react-router'

import { AuthMenu } from './features/auth/AuthMenu'
import './App.css'

export function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <nav
          aria-label="Primary"
          className="mx-auto flex max-w-5xl items-center justify-between"
        >
          <Link className="text-lg font-semibold" to="/">
            JuryStack
          </Link>
          <div className="flex items-center gap-5">
            <NavLink className="text-sm text-slate-300 hover:text-white" to="/">
              Gallery
            </NavLink>
            <NavLink
              className="text-sm text-slate-300 hover:text-white"
              to="/workspace"
            >
              Workspace
            </NavLink>
            <NavLink
              className="text-sm text-slate-300 hover:text-white"
              to="/organizer/events"
            >
              Events
            </NavLink>
            <NavLink
              className="text-sm text-slate-300 hover:text-white"
              to="/organizer/judging"
            >
              Judging setup
            </NavLink>
            <NavLink
              className="text-sm text-slate-300 hover:text-white"
              to="/judge/assignments"
            >
              Assignments
            </NavLink>
            <AuthMenu />
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-12">
        <Outlet />
      </main>
    </div>
  )
}
