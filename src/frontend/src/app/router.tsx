import { createBrowserRouter } from 'react-router'

import { App } from '../App'
import { LoginPage } from '../features/auth/LoginPage'
import { ScaffoldPage } from '../shared/ScaffoldPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <ScaffoldPage /> },
      { path: 'login', element: <LoginPage /> },
    ],
  },
])
