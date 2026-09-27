import { createBrowserRouter } from 'react-router'

import { App } from '../App'
import { LoginPage } from '../features/auth/LoginPage'
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
      { path: 'workspace', element: <ParticipantPage /> },
      { path: 'workspace/projects/new', element: <ProjectEditorPage /> },
      {
        path: 'workspace/projects/:projectId/edit',
        element: <ProjectEditorPage />,
      },
      { path: 'organizer/events', element: <OrganizerEventsPage /> },
    ],
  },
])
