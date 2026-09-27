import { useTheme, type ThemePreference } from './theme-context'

const options: Array<{
  value: ThemePreference
  label: string
  icon: string
}> = [
  { value: 'system', label: 'System', icon: '◩' },
  { value: 'light', label: 'Light', icon: '☀' },
  { value: 'dark', label: 'Dark', icon: '◐' },
]

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { preference, setPreference } = useTheme()
  const dark =
    preference === 'dark' ||
    (preference === 'system' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches)

  if (compact) {
    return (
      <button
        aria-label={`Switch to ${dark ? 'light' : 'dark'} theme`}
        className="theme-icon-button"
        onClick={() => setPreference(dark ? 'light' : 'dark')}
        title={`Switch to ${dark ? 'light' : 'dark'} theme`}
        type="button"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
          {dark ? (
            <>
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
            </>
          ) : (
            <path d="M20.2 15.1A8.5 8.5 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z" />
          )}
        </svg>
      </button>
    )
  }

  return (
    <fieldset className="theme-switcher">
      <legend className={compact ? 'sr-only' : 'field-label'}>
        Appearance
      </legend>
      <div className="theme-options" aria-label="Color theme">
        {options.map((option) => (
          <button
            aria-pressed={preference === option.value}
            className="theme-option"
            key={option.value}
            onClick={() => setPreference(option.value)}
            type="button"
          >
            <span aria-hidden="true">{option.icon}</span>
            <span>{option.label}</span>
          </button>
        ))}
      </div>
    </fieldset>
  )
}
