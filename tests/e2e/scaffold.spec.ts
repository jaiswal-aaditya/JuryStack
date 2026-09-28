import { expect, test } from '@playwright/test'

test('browses the public gallery and shows the deadline state', async ({
  page,
}) => {
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: /projects built/i }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: 'Glass Signal' })).toBeVisible()
  await page.getByRole('link', { name: 'Glass Signal' }).click()
  await expect(
    page.getByRole('heading', { name: 'Glass Signal' }),
  ).toBeVisible()

  await page.goto('/login')
  await page.getByLabel('Email').fill('priya1@example.org')
  await page.getByRole('textbox', { name: 'Password' }).fill('jurystack-local-demo')
  await page.getByRole('button', { name: 'Log in' }).click()
  await page.waitForURL('**/dashboard')
  await page.goto('/workspace/projects/new')
  await expect(page.getByRole('alert')).toContainText(
    'submission deadline has passed',
  )
})
