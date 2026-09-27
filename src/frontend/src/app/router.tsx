import { createBrowserRouter } from 'react-router'

import { App } from '../App'
import { LoginPage } from '../features/auth/LoginPage'
import { ProfilePage } from '../features/auth/ProfilePage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { JudgeAssignmentsPage } from '../features/judging/JudgeAssignmentsPage'
import { JudgeInvitationPage } from '../features/judging/JudgeInvitationPage'
import { JudgeScorecardPage } from '../features/judging/JudgeScorecardPage'
import { OrganizerJudgingPage } from '../features/judging/OrganizerJudgingPage'
import { OrganizerOperationsPage } from '../features/judging/OrganizerOperationsPage'
import { GalleryPage } from '../features/tier1/GalleryPage'
import { OrganizerEventsPage } from '../features/tier1/OrganizerEventsPage'
import { ParticipantPage } from '../features/tier1/ParticipantPage'
import { ProjectDetailPage } from '../features/tier1/ProjectDetailPage'
import { ProjectEditorPage } from '../features/tier1/ProjectEditorPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <GalleryPage /> },
      { path: 'projects/:projectId', element: <ProjectDetailPage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'workspace', element: <ParticipantPage /> },
      { path: 'workspace/projects/new', element: <ProjectEditorPage /> },
      {
        path: 'workspace/projects/:projectId/edit',
        element: <ProjectEditorPage />,
      },
      { path: 'organizer/events', element: <OrganizerEventsPage /> },
      { path: 'organizer/judging', element: <OrganizerJudgingPage /> },
      { path: 'organizer/operations', element: <OrganizerOperationsPage /> },
      { path: 'judge/assignments', element: <JudgeAssignmentsPage /> },
      {
        path: 'judge/projects/:projectId/score',
        element: <JudgeScorecardPage />,
      },
      { path: 'judge-invitations/:token', element: <JudgeInvitationPage /> },
    ],
  },
])
