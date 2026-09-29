import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { gallery, type Project } from './api'
import { ErrorState } from '../../shared/AsyncState'

type SortMode = 'newest' | 'oldest' | 'az' | 'za' | 'track'
type ViewMode = 'grid' | 'list'

const sortModes = new Set<SortMode>(['newest', 'oldest', 'az', 'za', 'track'])

function SearchIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <path d="m16 16 4 4" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
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
      <path d="M7.5 16.25H18M8.5 7.5h6M8.5 10.5h4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.7" />
    </svg>
  )
}

function CalendarIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 16 16">
      <rect x="2" y="3.5" width="12" height="10.5" rx="2" stroke="currentColor" />
      <path d="M5 2v3M11 2v3M2 6.5h12" stroke="currentColor" strokeLinecap="round" />
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

function HighlightedText({ text, query }: { text: string; query: string }) {
  const term = query.trim()
  if (!term) return <>{text}</>
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const parts = text.split(new RegExp(`(${escaped})`, 'ig'))
  return (
    <>
      {parts.map((part, index) =>
        part.toLocaleLowerCase() === term.toLocaleLowerCase() ? (
          <mark key={`${part}-${index}`}>{part}</mark>
        ) : (
          part
        ),
      )}
    </>
  )
}

async function loadAllProjects() {
  const pageSize = 100
  const first = await gallery('', '', pageSize, 0)
  const offsets = Array.from(
    { length: Math.ceil(first.total / pageSize) - 1 },
    (_, index) => (index + 1) * pageSize,
  )
  if (!offsets.length) return first
  const pages = await Promise.all(offsets.map((offset) => gallery('', '', pageSize, offset)))
  return { total: first.total, items: [...first.items, ...pages.flatMap((page) => page.items)] }
}

function storedViewMode(): ViewMode {
  try {
    return window.localStorage.getItem('jurystack-project-view') === 'list' ? 'list' : 'grid'
  } catch {
    return 'grid'
  }
}

export function GalleryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('q') ?? ''
  const tracks = Array.from(new Set(searchParams.getAll('track')))
  const requestedSort = searchParams.get('sort') as SortMode | null
  const sortBy = requestedSort && sortModes.has(requestedSort) ? requestedSort : 'newest'
  const viewParam = searchParams.get('view')
  const validView = viewParam === 'grid' || viewParam === 'list'
  const [savedView] = useState(storedViewMode)
  const viewMode: ViewMode = viewParam === 'list' ? 'list' : viewParam === 'grid' ? 'grid' : savedView
  const searchRef = useRef<HTMLInputElement>(null)
  const scrollTopRef = useRef<HTMLButtonElement>(null)
  const [showScrollTop, setShowScrollTop] = useState(false)
  const [openPeekId, setOpenPeekId] = useState<string | null>(null)
  const peekToggleRefs = useRef(new Map<string, HTMLButtonElement>())
  const all = useQuery({ queryKey: ['gallery', 'all'], queryFn: loadAllProjects })
  const projects = all.data?.items ?? []

  const updateUrl = useCallback(
    (updates: { search?: string; tracks?: string[]; sort?: SortMode; view?: ViewMode }, replace = false) => {
      const next = new URLSearchParams(searchParams)
      const nextSearch = updates.search ?? search
      const nextTracks = updates.tracks ?? tracks
      const nextSort = updates.sort ?? sortBy
      const nextView = updates.view ?? viewMode
      if (nextSearch) next.set('q', nextSearch)
      else next.delete('q')
      next.delete('track')
      nextTracks.forEach((track) => next.append('track', track))
      next.set('sort', nextSort)
      next.set('view', nextView)
      setSearchParams(next, { replace, preventScrollReset: true })
    },
    [search, searchParams, setSearchParams, sortBy, tracks, viewMode],
  )

  useEffect(() => {
    if (!requestedSort || !sortModes.has(requestedSort) || !validView) {
      updateUrl({ sort: sortBy, view: viewMode }, true)
    }
  }, [requestedSort, sortBy, updateUrl, validView, viewMode])

  useEffect(() => {
    try {
      window.localStorage.setItem('jurystack-project-view', viewMode)
    } catch {
      // The URL still preserves the view when storage is unavailable.
    }
  }, [viewMode])

  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const typing = target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA' || target?.isContentEditable
      if (event.key === '/' && !typing) {
        event.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', focusSearch)
    return () => window.removeEventListener('keydown', focusSearch)
  }, [])

  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 420)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!openPeekId) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      const toggle = peekToggleRefs.current.get(openPeekId)
      setOpenPeekId(null)
      requestAnimationFrame(() => toggle?.focus())
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [openPeekId])

  const trackMap = new Map<string, { name: string; count: number }>()
  for (const project of projects) {
    const current = trackMap.get(project.track_id)
    trackMap.set(project.track_id, { name: project.track_name, count: (current?.count ?? 0) + 1 })
  }
  const trackList = Array.from(trackMap)
  const filteredProjects = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    return projects.filter((project) => {
      const matchesTracks = tracks.length === 0 || tracks.includes(project.track_id)
      const text = `${project.title} ${project.team_name} ${project.summary} ${project.track_name}`.toLocaleLowerCase()
      return matchesTracks && (!query || text.includes(query))
    })
  }, [projects, search, tracks])
  const sortedProjects = useMemo(() => {
    const ordered = [...filteredProjects]
    ordered.sort((left, right) => {
      const titleCompare = left.title.localeCompare(right.title, undefined, { sensitivity: 'base' })
      if (sortBy === 'az') return titleCompare
      if (sortBy === 'za') return -titleCompare
      if (sortBy === 'track') {
        return left.track_name.localeCompare(right.track_name, undefined, { sensitivity: 'base' }) || titleCompare
      }
      const leftDate = Date.parse(left.submitted_at ?? '') || 0
      const rightDate = Date.parse(right.submitted_at ?? '') || 0
      return sortBy === 'oldest' ? leftDate - rightDate : rightDate - leftDate
    })
    return ordered
  }, [filteredProjects, sortBy])

  const hasActiveFilters = Boolean(search || tracks.length)
  const clearFilters = () => updateUrl({ search: '', tracks: [] })
  const toggleTrack = (trackId: string) => {
    const nextTracks = tracks.includes(trackId)
      ? tracks.filter((selected) => selected !== trackId)
      : [...tracks, trackId]
    updateUrl({ tracks: nextTracks })
  }
  const toggleView = (view: ViewMode) => updateUrl({ view })

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
              onChange={(event) => updateUrl({ search: event.target.value }, true)}
              placeholder="Search projects or teams"
              ref={searchRef}
              type="search"
              value={search}
            />
            {search ? (
              <button aria-label="Clear project search" className="search-clear" onClick={() => { updateUrl({ search: '' }, true); searchRef.current?.focus() }} type="button">×</button>
            ) : (
              <kbd aria-hidden="true">/</kbd>
            )}
          </span>
        </label>
        <div className="track-filter" aria-label="Filter by track" role="group">
          <span className="field-label">Track</span>
          <div className="track-pills">
            <button aria-pressed={tracks.length === 0} className="track-pill" onClick={() => updateUrl({ tracks: [] })} type="button">
              All <span>{all.data?.total ?? 0}</span>
            </button>
            {trackList.map(([id, track]) => (
              <button aria-pressed={tracks.includes(id)} className="track-pill" key={id} onClick={() => toggleTrack(id)} type="button">
                {track.name} <span>{track.count}</span>
              </button>
            ))}
          </div>
        </div>
        {hasActiveFilters && <button className="clear-filters filter-clear-button" onClick={clearFilters} type="button">Clear filters</button>}
      </div>

      <div className="gallery-results">
        <div className="results-heading">
          <h2>{hasActiveFilters ? 'Filtered projects' : 'All projects'}</h2>
          <div className="results-tools">
            {all.data && <span>{filteredProjects.length} results</span>}
            <label className="sort-control">
              <span className="sr-only">Sort projects</span>
              <select aria-label="Sort projects" onChange={(event) => updateUrl({ sort: event.target.value as SortMode })} value={sortBy}>
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="az">A to Z</option>
                <option value="za">Z to A</option>
                <option value="track">Track</option>
              </select>
            </label>
            <div className="view-toggle" aria-label="Project view" role="group">
              <button aria-label="Grid view" aria-pressed={viewMode === 'grid'} onClick={() => toggleView('grid')} type="button"><span aria-hidden="true">▦</span></button>
              <button aria-label="List view" aria-pressed={viewMode === 'list'} onClick={() => toggleView('list')} type="button"><span aria-hidden="true">☷</span></button>
            </div>
          </div>
        </div>

        {all.isLoading && <GallerySkeleton />}
        {all.error && <ErrorState error={all.error} />}
        {all.data && sortedProjects.length === 0 && (
          <div className="empty-state gallery-empty-state">
            <span className="empty-icon" aria-hidden="true"><SearchIcon /></span>
            <p>No projects match your search or selected tracks.</p>
            <button className="button button-secondary" onClick={clearFilters} type="button">Clear filters</button>
          </div>
        )}
        <ul className={`project-grid ${viewMode === 'list' ? 'project-grid-list' : ''}`}>
          {sortedProjects.map((project) => (
            <ProjectCard
              key={project.id}
              isOpen={openPeekId === project.id}
              onTogglePeek={() => setOpenPeekId((current) => current === project.id ? null : project.id)}
              project={project}
              query={search}
              registerToggle={(element) => {
                if (element) peekToggleRefs.current.set(project.id, element)
                else peekToggleRefs.current.delete(project.id)
              }}
            />
          ))}
        </ul>
      </div>
      {showScrollTop && (
        <button
          aria-label="Scroll to top"
          className="scroll-top-button"
          onClick={() => window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })}
          ref={scrollTopRef}
          type="button"
        >
          ↑
        </button>
      )}
    </section>
  )
}

function ProjectCard({
  project,
  query,
  isOpen,
  onTogglePeek,
  registerToggle,
}: {
  project: Project
  query: string
  isOpen: boolean
  onTogglePeek: () => void
  registerToggle: (element: HTMLButtonElement | null) => void
}) {
  const panelId = `quick-peek-${project.id}`
  const toggleRef = useRef<HTMLButtonElement>(null)
  return (
    <li className="project-card">
      <span className="badge badge-blue"><HighlightedText text={project.track_name} query={query} /></span>
      <h3>
        <Link className="project-link" to={`/projects/${project.id}`}><HighlightedText text={project.title} query={query} /></Link>
      </h3>
      <p className="project-team">By <HighlightedText text={project.team_name} query={query} /></p>
      <p className="project-summary"><HighlightedText text={project.summary} query={query} /></p>
      <div className={`project-peek ${isOpen ? 'is-open' : ''}`}>
        <button
          aria-controls={panelId}
          aria-expanded={isOpen}
          className="project-peek-toggle"
          onClick={onTogglePeek}
          ref={(element) => {
            toggleRef.current = element
            registerToggle(element)
          }}
          type="button"
        >
          <span>Quick peek</span>
          <span aria-hidden="true" className="peek-indicator"><svg viewBox="0 0 12 12" fill="none"><path d="M6 2.5v7M2.5 6h7" /></svg></span>
        </button>
        <div aria-hidden={!isOpen} className="project-peek-clip" id={panelId}>
          <div className="project-peek-content">
      <button aria-label="Close quick peek" className="peek-close" onClick={() => { onTogglePeek(); requestAnimationFrame(() => toggleRef.current?.focus()) }} type="button">×</button>
            <p>{project.summary}</p>
            <div className="peek-details-row">
              <span className="peek-submitted"><CalendarIcon /> Submitted {project.submitted_at ? new Date(project.submitted_at).toLocaleDateString() : 'date unavailable'}</span>
              <a className="repository-pill" href={project.repo_url} rel="noreferrer" target="_blank">Open repository <span aria-hidden="true">↗</span></a>
            </div>
          </div>
        </div>
      </div>
      <div className="project-meta">
        <span className="repo-badge"><RepositoryIcon /> Repository</span>
        <span className="status-dot"><i /> Submitted</span>
      </div>
      <Link className="card-action" to={`/projects/${project.id}`}>View project <span aria-hidden="true">→</span></Link>
    </li>
  )
}
