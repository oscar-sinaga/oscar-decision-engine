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

async function apiToken(request: APIRequestContext, username: string): Promise<string> {
	const response = await request.post(`${API_BASE}/v1/auth/login`, {
		data: { username, password: PASSWORD }
	});
	expect(response.ok()).toBeTruthy();
	return (await response.json()).access_token as string;
}

test('catalog output, expression authoring, preview, and generated test form', async ({
	page,
	request
}) => {
	const suffix = Date.now().toString(36).toUpperCase();
	const featurePath = `outputs.e2e_limit_${suffix.toLowerCase()}`;
	const ruleCode = `E2E_EXPR_${suffix}`;

	await login(page, 'admin');
	await page.goto('/features');
	await page.getByRole('button', { name: 'New feature' }).click();
	// The create form lives in a Sheet (drawer) since the FR2 redesign.
	const featureCard = page.locator('[data-slot="sheet-content"]');
	await featureCard.getByLabel('Path (dotted)').fill(featurePath);
	await featureCard.getByLabel('Label').fill(`E2E limit ${suffix}`);
	await featureCard.getByLabel('Data type').selectOption('NUMBER');
	await featureCard.getByLabel('Source').selectOption('RULE_OUTPUT');
	await featureCard.getByLabel('Category').fill('DECISION');
	await featureCard.getByLabel('Writable output').check();
	await page.getByRole('button', { name: 'Create feature' }).click();
	await expect(
		page.locator('[data-sonner-toast]').filter({ hasText: 'Feature created' })
	).toBeVisible();
	await expect(page.getByTestId('features-table')).toContainText(featurePath);

	await page.goto('/rules/new');
	await page.getByLabel('Rule code').fill(ruleCode);
	await page.getByLabel('Name').fill(`E2E expression ${suffix}`);
	await page.getByLabel('Rule kind').selectOption('EXPRESSION');
	await page.getByLabel('Output target').selectOption(featurePath);
	await page.getByLabel('OSCAR expression').fill('loan.requested_amount * 0.8');
	await expect(page.getByText(/Valid · NUMBER/)).toBeVisible();
	// The SQL-style preview is a tab ("SQL preview") since the FR4 redesign.
	await page.getByRole('tab', { name: 'SQL preview' }).click();
	await expect(page.getByText('Preview only — OSCAR never executes SQL.')).toBeVisible();
	await page.getByRole('button', { name: 'Create draft rule' }).click();

	await expect(page.getByRole('heading', { name: ruleCode })).toBeVisible();
	await expect(page.getByText('Used by')).toBeVisible();
	// The test form lives in the "Test" tab since the FR4 redesign.
	await page.getByRole('tab', { name: 'Test' }).click();
	await expect(page.getByText('Test rule')).toBeVisible();
	const testCard = page.getByRole('tabpanel');
	await testCard.locator('input').first().fill('10000000');
	await page.getByRole('button', { name: 'Run test' }).click();
	await expect(testCard).toContainText(featurePath);

	// Back-end permission is also checked here so the journey cannot pass on UI-only hiding.
	const analystToken = await apiToken(request, 'riskanalyst');
	const denied = await request.post(`${API_BASE}/v1/expressions/validate`, {
		headers: { Authorization: `Bearer ${analystToken}` },
		data: { expression: 'loan.requested_amount * 0.8', expects: 'value' }
	});
	expect(denied.status()).toBe(403);
});
