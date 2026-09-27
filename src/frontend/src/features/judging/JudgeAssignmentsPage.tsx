import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { judgeProjects } from './api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'

export function JudgeAssignmentsPage() {
  const query = useQuery({
    queryKey: ['judge-projects'],
    queryFn: judgeProjects,
  })
  if (query.isLoading) return <Loading label="Loading your assignments…" />
  if (query.error) return <ErrorState error={query.error} />
  return (
    <section className="assignments-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Judge workspace</p>
          <h1>Your assigned projects</h1>
          <p>
            Evaluate only projects in your eligible tracks. Your scorecards
            remain private from peer judges.
          </p>
        </div>
        <span className="badge badge-blue">
          {query.data?.length ?? 0} assigned
        </span>
      </div>
      {query.data?.length === 0 && (
        <div className="mt-8">
          <EmptyState>No projects have been assigned to you.</EmptyState>
        </div>
      )}
      <ul className="assignment-grid">
        {query.data?.map((project) => (
          <li className="assignment-card panel" key={project.id}>
            <div className="assignment-badges">
              <span className="badge badge-blue">{project.track_name}</span>
              <span className="badge badge-green">Submitted</span>
            </div>
            <h2>{project.title}</h2>
            <p>{project.summary}</p>
            <div className="assignment-actions">
              <Link
                className="button button-secondary"
                to={`/projects/${project.id}`}
              >
                View submission
              </Link>
              <a
                className="button button-secondary"
                href={project.repo_url}
                rel="noreferrer"
                target="_blank"
              >
                Open repository
              </a>
              <Link
                className="button button-primary"
                to={`/judge/projects/${project.id}/score`}
              >
                Open scorecard
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
