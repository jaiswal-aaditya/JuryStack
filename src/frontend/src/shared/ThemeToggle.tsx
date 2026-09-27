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
