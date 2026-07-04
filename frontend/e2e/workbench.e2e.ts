// Critical end-to-end flows (docs/15: Playwright for critical flows).
// Requires the backend stack: `docker compose up -d postgres` + migrated/seeded
// backend on http://localhost:8000 (see backend/README.md).

import { expect, test } from '@playwright/test';

const USERS = { analyst: 'riskanalyst', password: 'OscarDemo123!' };

async function login(page: import('@playwright/test').Page, username: string) {
	await page.goto('/login');
	await page.getByLabel('Username').fill(username);
	await page.getByLabel('Password').fill(USERS.password);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page.getByTestId('main-nav')).toBeVisible();
}

test('login and view dashboard KPIs', async ({ page }) => {
	await login(page, USERS.analyst);
	await expect(page).toHaveURL(/\/dashboard/);
	await expect(page.getByTestId('kpi-cards')).toBeVisible();
	await expect(page.getByText('Approval rate')).toBeVisible();
});

test('run a simulation and inspect the outcome', async ({ page }) => {
	await login(page, USERS.analyst);
	await page.goto('/simulations');
	await page.getByTestId('run-simulation').click();
	await expect(page.getByTestId('sim-result')).toBeVisible({ timeout: 15_000 });
	await expect(page.getByTestId('sim-result')).toContainText('LEASEBACK_MOTOR');
});

test('browse decision history to the trace view', async ({ page }) => {
	await login(page, USERS.analyst);
	await page.goto('/decisions');
	await expect(page.getByTestId('decision-table')).toBeVisible();
	const firstDecision = page.getByTestId('decision-table').locator('tbody a').first();
	if ((await firstDecision.count()) > 0) {
		await firstDecision.click();
		await expect(page.getByTestId('decision-summary')).toBeVisible();
		await expect(page.getByTestId('trace-steps')).toBeVisible();
	}
});

test('unauthenticated visitors are redirected to login', async ({ page }) => {
	await page.goto('/decisions');
	await expect(page).toHaveURL(/\/login/);
});
