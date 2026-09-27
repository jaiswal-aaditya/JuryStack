import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import { JudgeAssignmentsPage } from '../features/judging/JudgeAssignmentsPage'

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

export { screen }
