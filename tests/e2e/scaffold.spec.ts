import { expect, test } from '@playwright/test'

test('loads the JuryStack application shell', async ({ page }) => {
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: /ready for implementation/i }),
  ).toBeVisible()
})
