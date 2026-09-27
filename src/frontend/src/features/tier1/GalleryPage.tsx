import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { gallery } from './api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'

export function GalleryPage() {
  const [search, setSearch] = useState('')
  const [trackId, setTrackId] = useState('')
  const all = useQuery({
    queryKey: ['gallery', 'all'],
    queryFn: () => gallery(),
  })
  const filtered = useQuery({
    queryKey: ['gallery', search, trackId],
    queryFn: () => gallery(search, trackId),
  })
  const tracks = Array.from(
    new Map(
      (all.data?.items ?? []).map((project) => [
        project.track_id,
        project.track_name,
      ]),
    ),
  )

  return (
    <section>
      <p className="text-sm font-medium uppercase tracking-widest text-cyan-400">
        Public gallery
      </p>
      <h1 className="mt-3 text-4xl font-bold">Projects built to be seen</h1>
      <div className="mt-8 grid gap-3 sm:grid-cols-[1fr_16rem]">
        <label>
          <span className="sr-only">Search projects</span>
          <input
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search projects or teams"
            type="search"
            value={search}
          />
        </label>
        <label>
          <span className="sr-only">Filter by track</span>
          <select
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            onChange={(event) => setTrackId(event.target.value)}
            value={trackId}
          >
            <option value="">All tracks</option>
            {tracks.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-8">
        {filtered.isLoading && <Loading label="Loading projects…" />}
        {filtered.error && <ErrorState error={filtered.error} />}
        {filtered.data?.items.length === 0 && (
          <EmptyState>No submitted projects match these filters.</EmptyState>
        )}
        <ul className="grid gap-4 sm:grid-cols-2">
          {filtered.data?.items.map((project) => (
            <li
              key={project.id}
              className="rounded-xl border border-slate-800 bg-slate-900 p-5"
            >
              <p className="text-xs uppercase tracking-wide text-cyan-400">
                {project.track_name}
              </p>
              <h2 className="mt-2 text-xl font-semibold">
                <Link
                  className="hover:text-cyan-300"
                  to={`/projects/${project.id}`}
                >
                  {project.title}
                </Link>
              </h2>
              <p className="mt-2 text-sm text-slate-400">{project.team_name}</p>
              <p className="mt-3 text-slate-300">{project.summary}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
