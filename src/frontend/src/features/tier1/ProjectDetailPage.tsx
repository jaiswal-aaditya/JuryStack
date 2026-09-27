import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { publicProject } from './api'
import { ErrorState, Loading } from '../../shared/AsyncState'

export function ProjectDetailPage() {
  const { projectId = '' } = useParams()
  const project = useQuery({
    queryKey: ['public-project', projectId],
    queryFn: () => publicProject(projectId),
  })
  if (project.isLoading) return <Loading label="Loading project…" />
  if (project.error) return <ErrorState error={project.error} />
  if (!project.data) return null
  return (
    <article className="max-w-3xl">
      <Link className="text-cyan-300" to="/">
        ← Back to gallery
      </Link>
      <p className="mt-8 text-sm uppercase tracking-wide text-cyan-400">
        {project.data.track_name}
      </p>
      <h1 className="mt-2 text-4xl font-bold">{project.data.title}</h1>
      <p className="mt-2 text-slate-400">Built by {project.data.team_name}</p>
      <p className="mt-8 text-lg text-slate-200">{project.data.summary}</p>
      <a
        className="mt-8 inline-block rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950"
        href={project.data.repo_url}
        rel="noreferrer"
        target="_blank"
      >
        View repository
      </a>
    </article>
  )
}
