import { useQuery } from '@tanstack/react-query'

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
    <section>
      <p className="text-sm uppercase tracking-widest text-cyan-400">Judge</p>
      <h1 className="mt-2 text-3xl font-bold">Your assigned projects</h1>
      <p className="mt-3 text-slate-400">
        Only assignments in your eligible tracks are shown.
      </p>
      {query.data?.length === 0 && (
        <div className="mt-8">
          <EmptyState>No projects have been assigned to you.</EmptyState>
        </div>
      )}
      <ul className="mt-8 grid gap-5 md:grid-cols-2">
        {query.data?.map((project) => (
          <li
            className="rounded-xl border border-slate-800 bg-slate-900 p-5"
            key={project.id}
          >
            <p className="text-sm text-cyan-300">{project.track_name}</p>
            <h2 className="mt-2 text-xl font-semibold">{project.title}</h2>
            <p className="mt-3 text-slate-300">{project.summary}</p>
            <a
              className="mt-4 inline-block text-cyan-300"
              href={project.repo_url}
              rel="noreferrer"
              target="_blank"
            >
              Open repository
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
