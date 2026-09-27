import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'

import { gallery } from './api'
import { EmptyState, ErrorState } from '../../shared/AsyncState'

function SearchIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <path
        d="m16 16 4 4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="2"
      />
    </svg>
  )
}

function RepositoryIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 24 24">
      <path
        d="M6 3.75h9.25A2.75 2.75 0 0 1 18 6.5v13.75H7.5A2.5 2.5 0 0 1 5 17.75V4.75c0-.55.45-1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M7.5 16.25H18M8.5 7.5h6M8.5 10.5h4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function GallerySkeleton() {
  return (
    <div className="gallery-skeleton" role="status">
      <p>Loading projects…</p>
      <div className="project-grid" aria-hidden="true">
        {[0, 1, 2, 3, 4, 5].map((item) => (
          <div className="project-card skeleton-card" key={item}>
            <span className="skeleton skeleton-pill" />
            <span className="skeleton skeleton-title" />
            <span className="skeleton skeleton-copy" />
            <span className="skeleton skeleton-copy skeleton-short" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function GalleryPage() {
  const [search, setSearch] = useState('')
  const [trackId, setTrackId] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)
  const all = useQuery({
    queryKey: ['gallery', 'all'],
    queryFn: () => gallery(),
  })
  const filtered = useQuery({
    queryKey: ['gallery', search, trackId],
    queryFn: () => gallery(search, trackId),
  })
  const trackMap = new Map<string, { name: string; count: number }>()
  for (const project of all.data?.items ?? []) {
    const current = trackMap.get(project.track_id)
    trackMap.set(project.track_id, {
      name: project.track_name,
      count: (current?.count ?? 0) + 1,
    })
  }
  const tracks = Array.from(trackMap)

  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const typing =
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable
      if (event.key === '/' && !typing) {
        event.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', focusSearch)
    return () => window.removeEventListener('keydown', focusSearch)
  }, [])

  return (
    <section className="gallery-page">
      <div className="gallery-hero">
        <div>
          <p className="eyebrow">Public project gallery</p>
          <h1>Projects built to be seen</h1>
          <p>
            JuryStack is a modern, open-source, self-hostable hackathon platform
            for the entire event lifecycle—from teams and submissions to
            judging, normalization, results, and export.
          </p>
        </div>
        <div className="gallery-stat">
          <strong>{all.data?.total ?? '—'}</strong>
          <span>submitted projects</span>
        </div>
      </div>
      <div className="filter-bar panel">
        <label className="search-field">
          <span className="field-label">Search projects</span>
          <span className="search-control">
            <SearchIcon />
            <input
              className="input"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search projects or teams"
              ref={searchRef}
              type="search"
              value={search}
            />
            {search ? (
              <button
                aria-label="Clear project search"
                className="search-clear"
                onClick={() => {
                  setSearch('')
                  searchRef.current?.focus()
                }}
                type="button"
              >
                ×
              </button>
            ) : (
              <kbd aria-hidden="true">/</kbd>
            )}
          </span>
        </label>
        <div className="track-filter" aria-label="Filter by track" role="group">
          <span className="field-label">Track</span>
          <div className="track-pills">
            <button
              aria-pressed={trackId === ''}
              className="track-pill"
              onClick={() => setTrackId('')}
              type="button"
            >
              All <span>{all.data?.total ?? 0}</span>
            </button>
            {tracks.map(([id, track]) => (
              <button
                aria-pressed={trackId === id}
                className="track-pill"
                key={id}
                onClick={() => setTrackId(id)}
                type="button"
              >
                {track.name} <span>{track.count}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="gallery-results">
        <div className="results-heading">
          <h2>{search || trackId ? 'Filtered projects' : 'All projects'}</h2>
          {filtered.data && <span>{filtered.data.total} results</span>}
        </div>
        {filtered.isLoading && <GallerySkeleton />}
        {filtered.error && <ErrorState error={filtered.error} />}
        {filtered.data?.items.length === 0 && (
          <EmptyState>No submitted projects match these filters.</EmptyState>
        )}
        <ul className="project-grid">
          {filtered.data?.items.map((project) => (
            <li key={project.id} className="project-card">
              <span className="badge badge-blue">{project.track_name}</span>
              <h3>
                <Link className="project-link" to={`/projects/${project.id}`}>
                  {project.title}
                </Link>
              </h3>
              <p className="project-team">By {project.team_name}</p>
              <p className="project-summary">{project.summary}</p>
              <div className="project-meta">
                <span className="repo-badge">
                  <RepositoryIcon /> Repository
                </span>
                <span className="status-dot">
                  <i /> Submitted
                </span>
              </div>
              <Link className="card-action" to={`/projects/${project.id}`}>
                View project <span aria-hidden="true">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
