export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message =
    error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div role="alert" className="alert alert-error">
      {message}
    </div>
  )
}

export function EmptyState({ children }: { children: string }) {
  return (
    <div className="empty-state">
      <span className="empty-icon" aria-hidden="true">
        <svg fill="none" viewBox="0 0 24 24">
          <path
            d="M7 4.5h8.5L19 8v11.5H7a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path
            d="M15 4.5V8h4M8.5 12h7M8.5 15h4.5"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.6"
          />
        </svg>
      </span>
      <p>{children}</p>
    </div>
  )
}
