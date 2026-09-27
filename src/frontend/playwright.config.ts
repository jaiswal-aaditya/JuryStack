import { defineConfig } from '@playwright/test'

const externalBaseUrl = process.env.JURYSTACK_TEST_BASE_URL

export default defineConfig({
  testDir: '../../tests/e2e',
  use: { baseURL: externalBaseUrl ?? 'http://127.0.0.1:4173' },
  webServer: externalBaseUrl
    ? undefined
    : {
        command: 'pnpm preview',
        port: 4173,
        reuseExistingServer: true,
      },
})
