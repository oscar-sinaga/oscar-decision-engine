import { expect, test } from '@playwright/test';

const DEMO_PASSWORD = 'OscarDemo123!';

async function login(page: import('@playwright/test').Page): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill('admin');
	await page.getByLabel('Password').fill(DEMO_PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(/\/dashboard$/);
}

test('audit row opens metadata and field-level diff drawer', async ({ page }) => {
	await login(page);
	// A fresh CI database has no audit entries until a state change is performed.
	await page.goto('/simulations');
	await page.getByTestId('run-simulation').click();
	await expect(page.getByTestId('sim-result')).toBeVisible({ timeout: 15_000 });
	await page.goto('/audit');
	// Skeleton rows are visible before data arrives, but have no click handler.
	// Select actual event content rather than clicking the first placeholder row.
	const firstRow = page
		.getByTestId('audit-table')
		.locator('tbody tr')
		.filter({ hasText: 'SIMULATION_EXECUTED' })
		.first();
	await expect(firstRow).toBeVisible();
	await firstRow.click();
	await expect(page.getByText('Field changes', { exact: true })).toBeVisible();
	await expect(page.getByText('Metadata', { exact: true })).toBeVisible();
});

test('governance actions require a reason and user roles open in a dialog', async ({ page }) => {
	await login(page);
	await page.goto('/admin');
	const approve = page.getByRole('button', { name: 'Approve', exact: true }).first();
	if (await approve.isVisible()) {
		await approve.click();
		await expect(page.getByLabel('Reason')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Approve & activate' })).toBeDisabled();
		await page.getByRole('button', { name: 'Cancel' }).click();
	}
	await page.getByRole('tab', { name: 'Users' }).click();
	await page.getByRole('button', { name: 'Edit roles' }).first().click();
	await expect(page.getByRole('dialog')).toContainText('Edit roles');
});
