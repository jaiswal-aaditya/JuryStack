import { useEffect, useRef } from 'react'

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  pending = false,
  onCancel,
  onConfirm,
}: {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  pending?: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !pending) onCancel()
    }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [onCancel, open, pending])
  if (!open) return null
  return (
    <div
      className="dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !pending) onCancel()
      }}
    >
      <section
        aria-describedby="confirm-description"
        aria-labelledby="confirm-title"
        aria-modal="true"
        className="dialog"
        role="dialog"
      >
        <div className="dialog-icon" aria-hidden="true">
          ✓
        </div>
        <h2 id="confirm-title">{title}</h2>
        <p id="confirm-description">{description}</p>
        <div className="dialog-actions">
          <button
            className="button button-secondary"
            disabled={pending}
            onClick={onCancel}
            ref={cancelRef}
            type="button"
          >
            Keep editing
          </button>
          <button
            className="button button-primary"
            disabled={pending}
            onClick={onConfirm}
            type="button"
          >
            {pending ? 'Submitting…' : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}
