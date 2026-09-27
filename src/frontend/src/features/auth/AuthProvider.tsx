import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from './api'
import { AuthContext } from './context'
const currentUserKey = ['auth', 'current-user'] as const

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const currentUser = useQuery({
    queryKey: currentUserKey,
    queryFn: fetchCurrentUser,
    retry: false,
  })
  const login = useMutation({
    mutationFn: loginRequest,
    onSuccess: (user) => queryClient.setQueryData(currentUserKey, user),
  })
  const logout = useMutation({
    mutationFn: logoutRequest,
    onSuccess: () => queryClient.setQueryData(currentUserKey, null),
  })

  return (
    <AuthContext.Provider
      value={{
        user: currentUser.data ?? null,
        isLoading: currentUser.isLoading,
        error: currentUser.error,
        login: login.mutateAsync,
        logout: logout.mutateAsync,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
