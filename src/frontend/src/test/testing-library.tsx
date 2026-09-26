import { render, screen } from '@testing-library/react'

import { ScaffoldPage } from '../shared/ScaffoldPage'

export function renderScaffoldPage() {
  return render(<ScaffoldPage />)
}

export { screen }
