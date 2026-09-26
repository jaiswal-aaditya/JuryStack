import { describe, expect, it } from 'vitest'

import {
  renderScaffoldPage,
  screen,
} from '../../src/frontend/src/test/testing-library'

describe('ScaffoldPage', () => {
  it('identifies the application scaffold', () => {
    renderScaffoldPage()

    expect(
      screen.getByRole('heading', { name: /ready for implementation/i }),
    ).toBeVisible()
  })
})
