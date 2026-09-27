import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { ToastContext } from './toast-context'

export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')
  const notify = useCallback((next: string) => {
    setMessage(next)
    window.setTimeout(() => setMessage(''), 3200)
  }, [])
  const value = useMemo(() => ({ notify }), [notify])
  return (
    <ToastContext.Provider value={value}>
      {children}
      {message && (
        <div className="toast" role="status">
          <span className="toast-mark" aria-hidden="true">
            ✓
          </span>
          {message}
        </div>
      )}
    </ToastContext.Provider>
  )
}
