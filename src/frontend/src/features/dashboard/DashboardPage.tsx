import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { useAuth } from '../auth/context'
import { judgeProjects } from '../judging/api'
import { events, myProjects, teams } from '../tier1/api'
import { EmptyState, ErrorState, Loading } from '../../shared/AsyncState'

function Metric({
  label,
  value,
  hint,
}: {
  label: string
  value: number
  hint: string
}) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
      <small>{hint}</small>
    </div>
  )
}

function JudgeDashboard() {
  const query = useQuery({
    queryKey: ['judge-projects'],
    queryFn: judgeProjects,
  })
  if (query.isLoading) return <Loading label="Loading your judging overview…" />
  if (query.error) return <ErrorState error={query.error} />
  return (
    <>
      <div className="metrics-grid">
        <Metric
          label="Assigned projects"
          value={query.data?.length ?? 0}
          hint="Within your eligible tracks"
        />
      </div>
      <div className="panel action-panel">
        <div>
          <h2>Ready to evaluate?</h2>
          <p>Open your assigned projects and continue private scorecards.</p>
        </div>
        <Link className="button button-primary" to="/judge/assignments">
          View assignments
        </Link>
      </div>
      {query.data?.length === 0 && (
        <EmptyState>No projects have been assigned to you yet.</EmptyState>
      )}
    </>
  )
}

function ParticipantDashboard() {
  const teamQuery = useQuery({ queryKey: ['teams'], queryFn: teams })
  const projectQuery = useQuery({
    queryKey: ['my-projects'],
    queryFn: myProjects,
  })
  if (teamQuery.isLoading || projectQuery.isLoading)
    return <Loading label="Loading your workspace overview…" />
  const error = teamQuery.error ?? projectQuery.error
  if (error) return <ErrorState error={error} />
  const submitted =
    projectQuery.data?.filter((project) => project.status === 'submitted')
      .length ?? 0
  return (
    <>
      <div className="metrics-grid">
        <Metric
          label="Teams"
          value={teamQuery.data?.length ?? 0}
          hint="Your event memberships"
        />
        <Metric
          label="Projects"
          value={projectQuery.data?.length ?? 0}
          hint={`${submitted} submitted`}
        />
      </div>
      <div className="panel action-panel">
        <div>
          <h2>Participant workspace</h2>
          <p>Manage teams, invitations, drafts, and submissions.</p>
        </div>
        <Link className="button button-primary" to="/workspace">
          Open workspace
        </Link>
      </div>
    </>
  )
}

function OrganizerDashboard() {
  const query = useQuery({ queryKey: ['events'], queryFn: events })
  if (query.isLoading) return <Loading label="Loading organizer overview…" />
  if (query.error) return <ErrorState error={query.error} />
  return (
    <>
      <div className="metrics-grid">
        <Metric
          label="Events"
          value={query.data?.length ?? 0}
          hint="Configured locally"
        />
        <Metric
          label="Management areas"
          value={3}
          hint="Events, judging, operations"
        />
      </div>
      <div className="quick-grid">
        <Link className="panel quick-link" to="/organizer/events">
          <span className="quick-icon">E</span>
          <div>
            <h2>Event setup</h2>
            <p>Configure dates, tracks, prizes, and questions.</p>
          </div>
          <span>→</span>
        </Link>
        <Link className="panel quick-link" to="/organizer/judging">
          <span className="quick-icon">J</span>
          <div>
            <h2>Judging setup</h2>
            <p>Manage rubrics, invitations, and assignments.</p>
          </div>
          <span>→</span>
        </Link>
        <Link className="panel quick-link" to="/organizer/operations">
          <span className="quick-icon">O</span>
          <div>
            <h2>Judging operations</h2>
            <p>Track completion, export results, and review audit history.</p>
          </div>
          <span>→</span>
        </Link>
      </div>
    </>
  )
}

export function DashboardPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) return <Loading label="Loading dashboard…" />
  if (!user)
    return <EmptyState>Log in to open your role-specific dashboard.</EmptyState>
  return (
    <section className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>Welcome back, {user.display_name.split(' ')[0]}</h1>
          <p>Here is the work that matters for your {user.role} role.</p>
        </div>
        <span className="badge badge-blue capitalize">{user.role}</span>
      </div>
      {user.role === 'judge' && <JudgeDashboard />}
      {user.role === 'participant' && <ParticipantDashboard />}
      {(user.role === 'organizer' || user.role === 'admin') && (
        <OrganizerDashboard />
      )}
    </section>
  )
}
