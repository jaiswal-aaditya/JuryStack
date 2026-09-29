import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ThemeContext, type ThemePreference } from './theme-context'

const storageKey = 'jurystack-theme'

function storedPreference(): ThemePreference {
  const value = localStorage.getItem(storageKey)
  return value === 'light' || value === 'dark' ? value : 'system'
}

function applyTheme(preference: ThemePreference) {
  const dark =
    preference === 'dark' ||
    (preference === 'system' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches)
  const resolved = dark ? 'dark' : 'light'
  document.documentElement.dataset.theme = resolved
  document.documentElement.style.colorScheme = resolved
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', dark ? '#171012' : '#fff8f1')
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState(storedPreference)

  useEffect(() => {
    applyTheme(preference)
    if (preference === 'system') localStorage.removeItem(storageKey)
    else localStorage.setItem(storageKey, preference)

    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => applyTheme(preference)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [preference])

  const value = useMemo(
    () => ({ preference, setPreference: setPreferenceState }),
    [preference],
  )
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
