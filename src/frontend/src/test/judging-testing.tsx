import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'

import { JudgeAssignmentsPage } from '../features/judging/JudgeAssignmentsPage'
import { JudgeScorecardPage } from '../features/judging/JudgeScorecardPage'

export function renderJudgeAssignments() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <JudgeAssignmentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

export function renderJudgeScorecard(projectId = 'prj_07') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/judge/projects/${projectId}/score`]}>
        <Routes>
          <Route
            element={<JudgeScorecardPage />}
            path="/judge/projects/:projectId/score"
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

export { fireEvent, screen }
