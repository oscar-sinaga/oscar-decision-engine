import { defineConfig } from '@playwright/test';

const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

export default defineConfig({
	use: {
		baseURL: process.env.OSCAR_WEB_BASE_URL ?? 'http://127.0.0.1:4173',
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
