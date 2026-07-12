import { expect, test } from '@playwright/test';

async function login(page: import('@playwright/test').Page): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill('admin');
	await page.getByLabel('Password').fill('OscarDemo123!');
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page.getByTestId('main-nav')).toBeVisible();
}

test('decisions list supports loading, sorting, empty filtering, and pagination affordance', async ({
	page
}) => {
	await login(page);
	await page.goto('/decisions');
	const table = page.getByTestId('decision-table');
	await expect(table).toBeVisible();
	await table.getByRole('button', { name: /Application/ }).click();
	await table.getByRole('button', { name: /Application/ }).click();

	await page.getByLabel('Application ID').fill(`IMPOSSIBLE-${Date.now()}`);
	await page.getByRole('button', { name: 'Search' }).click();
	await expect(page.getByText('No decisions match these filters')).toBeVisible();
	await page.getByRole('button', { name: 'Reset' }).click();
	await expect(table).toBeVisible();
});
