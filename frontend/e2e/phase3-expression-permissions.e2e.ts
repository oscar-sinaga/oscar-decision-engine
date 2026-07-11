import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API_BASE = process.env.OSCAR_API_BASE_URL ?? 'http://localhost:8000';
const PASSWORD = 'OscarDemo123!';

async function login(page: Page, username: string) {
	await page.goto('/login');
	await page.getByLabel('Username').fill(username);
	await page.getByLabel('Password').fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page.getByTestId('main-nav')).toBeVisible();
}

async function token(request: APIRequestContext, username: string): Promise<string> {
	const response = await request.post(`${API_BASE}/v1/auth/login`, {
		data: { username, password: PASSWORD }
	});
	expect(response.ok()).toBeTruthy();
	return (await response.json()).access_token as string;
}

test('expression authoring is visible to admin and rejected for analyst at the API', async ({
	page,
	request
}) => {
	await login(page, 'admin');
	await page.goto('/rules/new');
	await expect(page.getByLabel('Rule kind').locator('option[value="EXPRESSION"]')).toHaveCount(1);
	await page.getByLabel('Rule kind').selectOption('EXPRESSION');
	await expect(page.getByText('Safe expression')).toBeVisible();

	const adminToken = await token(request, 'admin');
	const allowed = await request.post(`${API_BASE}/v1/expressions/validate`, {
		headers: { Authorization: `Bearer ${adminToken}` },
		data: { expression: 'loan.requested_amount * 0.8', expects: 'value' }
	});
	expect(allowed.status()).toBe(200);

	await page.evaluate(() => localStorage.clear());
	await login(page, 'riskanalyst');
	await page.goto('/rules/new');
	await expect(page.getByLabel('Rule kind').locator('option[value="EXPRESSION"]')).toHaveCount(0);

	const analystToken = await token(request, 'riskanalyst');
	const denied = await request.post(`${API_BASE}/v1/expressions/validate`, {
		headers: { Authorization: `Bearer ${analystToken}` },
		data: { expression: 'loan.requested_amount * 0.8', expects: 'value' }
	});
	expect(denied.status()).toBe(403);
});
