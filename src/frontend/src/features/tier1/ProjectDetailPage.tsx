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
    <article className="project-detail">
      <nav aria-label="Breadcrumb" className="breadcrumb">
        <Link to="/">Projects</Link>
        <span aria-hidden="true">/</span>
        <span>{project.data.title}</span>
      </nav>
      <div className="project-detail-grid">
        <div className="project-story">
          <span className="badge badge-blue">{project.data.track_name}</span>
          <h1>{project.data.title}</h1>
          <p className="project-byline">
            Built by <strong>{project.data.team_name}</strong>
          </p>
          <div className="project-summary-block">
            <p className="eyebrow">About the project</p>
            <p>{project.data.summary}</p>
          </div>
        </div>
        <aside className="panel project-sidebar" aria-label="Project details">
          <h2>Project details</h2>
          <dl>
            <div>
              <dt>Status</dt>
              <dd>
                <span className="badge badge-green">Submitted</span>
              </dd>
            </div>
            <div>
              <dt>Track</dt>
              <dd>{project.data.track_name}</dd>
            </div>
            <div>
              <dt>Team</dt>
              <dd>{project.data.team_name}</dd>
            </div>
            {project.data.submitted_at && (
              <div>
                <dt>Submitted</dt>
                <dd>{new Date(project.data.submitted_at).toLocaleString()}</dd>
              </div>
            )}
          </dl>
          <a
            className="button button-primary button-full"
            href={project.data.repo_url}
            rel="noreferrer"
            target="_blank"
          >
            View repository <span aria-hidden="true">↗</span>
          </a>
        </aside>
      </div>
    </article>
  )
}
