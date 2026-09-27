export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <p className="text-slate-300">{label}</p>
}

export function ErrorState({ error }: { error: unknown }) {
  const message =
    error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div
      role="alert"
      className="rounded border border-red-800 bg-red-950 p-4 text-red-200"
    >
      {message}
    </div>
  )
}

export function EmptyState({ children }: { children: string }) {
  return (
    <p className="rounded border border-dashed border-slate-700 p-6 text-slate-400">
      {children}
    </p>
  )
}
