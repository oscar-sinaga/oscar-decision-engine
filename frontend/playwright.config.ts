import { defineConfig } from '@playwright/test';

const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

export default defineConfig({
	// E2E journeys mutate one shared acceptance database and must remain deterministic.
	workers: 1,
	use: {
		baseURL: process.env.OSCAR_WEB_BASE_URL ?? 'http://127.0.0.1:4173',
		// Keep evidence when a journey fails so flakes can be diagnosed, not guessed at.
		trace: 'retain-on-failure',
		launchOptions: chromiumExecutable
			? { executablePath: chromiumExecutable, args: ['--no-sandbox'] }
			: undefined
	},
	webServer: {
		command: 'npm run build && npm run preview -- --host 127.0.0.1',
		port: 4173,
		reuseExistingServer: true
	},
	testMatch: '**/*.e2e.{ts,js}'
});
