import { expect, test } from '@playwright/test';

const DEMO_PASSWORD = 'OscarDemo123!';

async function login(page: import('@playwright/test').Page): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill('admin');
	await page.getByLabel('Password').fill(DEMO_PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(/\/dashboard$/);
}

test('shell provides grouped navigation, breadcrumbs, collapse, and user sign out', async ({
	page
}) => {
	await login(page);
	const nav = page.getByTestId('main-nav');
	await expect(nav).toContainText('Dashboard');
	await expect(nav).toContainText('Decision Tables');
	await expect(page.getByText('Monitor', { exact: true })).toBeVisible();

	await page.getByLabel('Collapse navigation').first().click();
	await expect(nav.getByText('Dashboard', { exact: true })).toBeHidden();
	await page.getByLabel('Expand navigation').first().click();

	await page.goto('/decisions/example-id');
	await expect(page.getByText('Decisions', { exact: true }).first()).toBeVisible();

	await page.getByRole('button', { name: /admin|user/i }).click();
	await page.getByText('Sign out', { exact: true }).click();
	await expect(page).toHaveURL(/\/login$/);
});
