import { Link, Outlet } from 'react-router'

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
          <span className="text-sm text-slate-400">Scaffold milestone</span>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-16">
        <Outlet />
      </main>
    </div>
  )
}
