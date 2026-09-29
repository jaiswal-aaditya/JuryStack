import { createBrowserRouter } from 'react-router'
import { lazy, Suspense, type ComponentType, type ReactNode } from 'react'

import { App } from '../App'
function lazyNamedPage(
  loader: () => Promise<unknown>,
  exportName: string,
) {
  return lazy(async () => ({
    default: (await loader() as Record<string, ComponentType>)[exportName],
  }))
}

const GalleryPage = lazyNamedPage(() => import('../features/tier1/GalleryPage'), 'GalleryPage')
const DashboardPage = lazyNamedPage(() => import('../features/dashboard/DashboardPage'), 'DashboardPage')
const JudgeAssignmentsPage = lazyNamedPage(() => import('../features/judging/JudgeAssignmentsPage'), 'JudgeAssignmentsPage')
const LoginPage = lazyNamedPage(() => import('../features/auth/LoginPage'), 'LoginPage')
const ProfilePage = lazyNamedPage(() => import('../features/auth/ProfilePage'), 'ProfilePage')
const JudgeInvitationPage = lazyNamedPage(() => import('../features/judging/JudgeInvitationPage'), 'JudgeInvitationPage')
const JudgeScorecardPage = lazyNamedPage(() => import('../features/judging/JudgeScorecardPage'), 'JudgeScorecardPage')
const OrganizerJudgingPage = lazyNamedPage(() => import('../features/judging/OrganizerJudgingPage'), 'OrganizerJudgingPage')
const OrganizerOperationsPage = lazyNamedPage(() => import('../features/judging/OrganizerOperationsPage'), 'OrganizerOperationsPage')
const OrganizerEventsPage = lazyNamedPage(() => import('../features/tier1/OrganizerEventsPage'), 'OrganizerEventsPage')
const ParticipantPage = lazyNamedPage(() => import('../features/tier1/ParticipantPage'), 'ParticipantPage')
const ProjectDetailPage = lazyNamedPage(() => import('../features/tier1/ProjectDetailPage'), 'ProjectDetailPage')
const ProjectEditorPage = lazyNamedPage(() => import('../features/tier1/ProjectEditorPage'), 'ProjectEditorPage')
const VotingPage = lazyNamedPage(() => import('../features/voting/VotingPage'), 'VotingPage')

function LazyRoute({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<div className="route-loading-skeleton" aria-hidden="true" />}>
      {children}
    </Suspense>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <LazyRoute><GalleryPage /></LazyRoute> },
      { path: 'projects/:projectId', element: <LazyRoute><ProjectDetailPage /></LazyRoute> },
      { path: 'login', element: <LazyRoute><LoginPage /></LazyRoute> },
      { path: 'dashboard', element: <LazyRoute><DashboardPage /></LazyRoute> },
      { path: 'profile', element: <LazyRoute><ProfilePage /></LazyRoute> },
      { path: 'workspace', element: <LazyRoute><ParticipantPage /></LazyRoute> },
      { path: 'workspace/projects/new', element: <LazyRoute><ProjectEditorPage /></LazyRoute> },
      {
        path: 'workspace/projects/:projectId/edit',
        element: <LazyRoute><ProjectEditorPage /></LazyRoute>,
      },
      { path: 'organizer/events', element: <LazyRoute><OrganizerEventsPage /></LazyRoute> },
      { path: 'organizer/judging', element: <LazyRoute><OrganizerJudgingPage /></LazyRoute> },
      { path: 'organizer/operations', element: <LazyRoute><OrganizerOperationsPage /></LazyRoute> },
      { path: 'judge/assignments', element: <LazyRoute><JudgeAssignmentsPage /></LazyRoute> },
      {
        path: 'judge/projects/:projectId/score',
        element: <LazyRoute><JudgeScorecardPage /></LazyRoute>,
      },
      { path: 'judge-invitations/:token', element: <LazyRoute><JudgeInvitationPage /></LazyRoute> },
      { path: 'vote/:token', element: <LazyRoute><VotingPage /></LazyRoute> },
    ],
  },
])
