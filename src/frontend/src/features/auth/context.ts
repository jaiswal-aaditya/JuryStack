import { createContext, useContext } from 'react'

import type { CurrentUser } from './api'

export interface AuthContextValue {
  user: CurrentUser | null
  isLoading: boolean
  error: Error | null
  login: (input: { email: string; password: string }) => Promise<CurrentUser>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
