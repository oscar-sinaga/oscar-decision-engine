import { expect, test } from '@playwright/test';

const DEMO_PASSWORD = 'OscarDemo123!';

async function login(page: import('@playwright/test').Page): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill('admin');
	await page.getByLabel('Password').fill(DEMO_PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(/\/dashboard$/);
}

test('audit row opens metadata and field-level diff drawer', async ({ page, request }) => {
	await login(page);
	// A fresh seed intentionally has no business audit rows. Create our own
	// synthetic audited feature instead of depending on a previous test run.
	const token = await page.evaluate(() => localStorage.getItem('oscar.token'));
	const created = await request.post(
		`${process.env.OSCAR_API_BASE_URL ?? 'http://localhost:8000'}/v1/features`,
		{
			headers: { Authorization: `Bearer ${token}` },
			data: {
				path: `outputs.audit_e2e_${Date.now()}`,
				label: 'Synthetic audit acceptance feature',
				data_type: 'NUMBER',
				source: 'RULE_OUTPUT',
				category: 'DECISION',
				writable: true
			}
		}
	);
	expect(created.status()).toBe(201);
	await page.goto('/audit');
	const firstRow = page.getByTestId('audit-table').locator('tbody tr').first();
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
