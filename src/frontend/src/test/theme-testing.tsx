import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ThemeProvider } from '../shared/ThemeProvider'
import { ThemeToggle } from '../shared/ThemeToggle'

export function renderThemeToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  )
}

export { cleanup, screen, userEvent, waitFor }
