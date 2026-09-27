import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'

import { judgeProjects, judgeScorecards } from './api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'

export function JudgeAssignmentsPage() {
  const [statusFilter, setStatusFilter] = useState('all')
  const query = useQuery({
    queryKey: ['judge-projects'],
    queryFn: judgeProjects,
  })
  const scorecardsQuery = useQuery({
    queryKey: ['judge-scorecards'],
    queryFn: judgeScorecards,
  })
  const scorecards = scorecardsQuery.data ?? []
  const scorecardByProject = useMemo(
    () => new Map(scorecards.map((scorecard) => [scorecard.project_id, scorecard])),
    [scorecards],
  )
  if (query.isLoading || scorecardsQuery.isLoading)
    return <Loading label="Loading your assignments…" />
  if (query.error || scorecardsQuery.error)
    return <ErrorState error={query.error ?? scorecardsQuery.error} />
  const projects = query.data ?? []
  const submittedCount = projects.filter(
    (project) => scorecardByProject.get(project.id)?.status === 'submitted',
  ).length
  const draftCount = projects.filter(
    (project) => scorecardByProject.get(project.id)?.status === 'draft',
  ).length
  const missingCount = projects.length - submittedCount - draftCount
  const visibleProjects = projects.filter((project) => {
    const status = scorecardByProject.get(project.id)?.status ?? 'missing'
    return statusFilter === 'all' || statusFilter === status
  })
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
        <span className="badge badge-blue">{projects.length} assigned</span>
      </div>
      {projects.length > 0 && (
        <div className="judge-workload panel">
          <div className="judge-workload-heading">
            <div>
              <span className="eyebrow">Your review desk</span>
              <h2>One project at a time</h2>
            </div>
            <strong>{submittedCount} <span>of {projects.length} complete</span></strong>
          </div>
          <div
            className="progress-track"
            role="progressbar"
            aria-label="Assigned scorecards submitted"
            aria-valuemin={0}
            aria-valuemax={projects.length}
            aria-valuenow={submittedCount}
          >
            <span style={{ width: `${projects.length ? (submittedCount / projects.length) * 100 : 0}%` }} />
          </div>
          <div className="judge-workload-legend">
            <span><i className="state-dot state-missing" /> {missingCount} to start</span>
            <span><i className="state-dot state-draft" /> {draftCount} in progress</span>
            <span><i className="state-dot state-submitted" /> {submittedCount} submitted</span>
          </div>
        </div>
      )}
      {projects.length === 0 && (
        <div className="mt-8">
          <EmptyState>No projects have been assigned to you.</EmptyState>
        </div>
      )}
      {projects.length > 0 && (
        <div className="assignment-filter-row" role="group" aria-label="Filter assignments">
          {[
            ['all', 'All projects', projects.length],
            ['missing', 'To start', missingCount],
            ['draft', 'In progress', draftCount],
            ['submitted', 'Submitted', submittedCount],
          ].map(([value, label, count]) => (
            <button
              aria-pressed={statusFilter === value}
              className="assignment-filter"
              key={value}
              onClick={() => setStatusFilter(String(value))}
              type="button"
            >
              {label} <span>{count}</span>
            </button>
          ))}
        </div>
      )}
      <ul className="assignment-grid">
        {visibleProjects.map((project) => {
          const scorecard = scorecardByProject.get(project.id)
          const status = scorecard?.status ?? 'missing'
          const label = status === 'submitted' ? 'Submitted' : status === 'draft' ? 'In progress' : 'To start'
          const scoredCriteria = scorecard?.criteria.filter((criterion) => criterion.score !== null).length ?? 0
          return (
          <li className="assignment-card panel" key={project.id}>
            <div className="assignment-badges">
              <span className="badge badge-blue">{project.track_name}</span>
              <span className={`badge assignment-state assignment-state-${status}`}>
                <i /> {label}
              </span>
            </div>
            <h2>{project.title}</h2>
            <p>{project.summary}</p>
            {scorecard && (
              <div className="assignment-card-progress">
                <span>{scoredCriteria} of {scorecard.criteria.length} criteria scored</span>
                <div className="progress-track" aria-hidden="true">
                  <span style={{ width: `${scorecard.criteria.length ? (scoredCriteria / scorecard.criteria.length) * 100 : 0}%` }} />
                </div>
              </div>
            )}
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
                {status === 'submitted' ? 'Review scorecard' : status === 'draft' ? 'Continue scoring' : 'Start scorecard'}
              </Link>
            </div>
          </li>
          )
        })}
      </ul>
      {projects.length > 0 && visibleProjects.length === 0 && (
        <EmptyState>No assignments match this status.</EmptyState>
      )}
    </section>
  )
}
