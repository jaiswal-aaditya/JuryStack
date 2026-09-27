import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router'

import { router } from './router'
import { AuthProvider } from '../features/auth/AuthProvider'
import { ThemeProvider } from '../shared/ThemeProvider'
import { ToastProvider } from '../shared/ToastProvider'

const queryClient = new QueryClient()

export function AppProviders() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ToastProvider>
            <RouterProvider router={router} />
          </ToastProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
