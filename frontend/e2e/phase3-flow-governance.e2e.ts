import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API_BASE = process.env.OSCAR_API_BASE_URL ?? 'http://localhost:8000';
const PASSWORD = 'OscarDemo123!';

type Json = Record<string, unknown>;

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

async function api<T>(
	request: APIRequestContext,
	method: 'get' | 'post',
	path: string,
	accessToken: string,
	data?: unknown
): Promise<T> {
	const response = await request[method](`${API_BASE}${path}`, {
		headers: { Authorization: `Bearer ${accessToken}` },
		data
	});
	expect(response.ok(), `${method.toUpperCase()} ${path}: ${await response.text()}`).toBeTruthy();
	return (await response.json()) as T;
}

function applicationPayload(segment: string): Json {
	return {
		application_id: `E2E-${Date.now()}`,
		product_type: 'MOTOR_LEASEBACK',
		segment,
		channel: 'E2E',
		applicant: {
			customer_id: 'E2E-CUSTOMER',
			age: 34,
			employment_type: 'EMPLOYEE',
			monthly_income: 8500000,
			existing_monthly_obligation: 2500000,
			internal_max_dpd_12m: 0
		},
		loan: { requested_amount: 15000000, requested_tenor_months: 24 },
		vehicle: {
			type: 'MOTOR',
			brand: 'Honda',
			model: 'Vario',
			year: 2020,
			appraisal_value: 18000000,
			ownership_status: 'OWNED'
		},
		bureau: { collectability: 'CURRENT', max_dpd_12m: 0, active_loan_count: 2 },
		fraud: {
			identity_match: true,
			document_match: true,
			blacklist_hit: false,
			device_risk_score: 0.12
		},
		model_outputs: { credit_score: 684, model_version: 'MOTOR_SCORE_V1' }
	};
}

const graph = {
	nodes: [
		{ node_key: 'start', node_type: 'START', position: { x: 0, y: 80 } },
		{
			node_key: 'validation',
			node_type: 'VALIDATION',
			name: 'Required fields',
			config: { required_fields: ['loan.requested_amount', 'vehicle.appraisal_value'] },
			position: { x: 240, y: 80 }
		},
		{
			node_key: 'calculation',
			node_type: 'CALCULATION',
			name: 'Derived values',
			config: { calculations: ['loan.ltv', 'affordability.dti', 'vehicle.age_years'] },
			position: { x: 480, y: 80 }
		},
		{
			node_key: 'affordability',
			node_type: 'RULE_SET',
			name: 'Affordability',
			reference_code: 'AFFORDABILITY_STANDARD',
			position: { x: 720, y: 80 }
		},
		{
			node_key: 'score',
			node_type: 'SCORECARD',
			name: 'Score',
			reference_code: 'MOTOR_SCORECARD',
			position: { x: 960, y: 80 }
		},
		{
			node_key: 'final',
			node_type: 'DECISION_TABLE',
			name: 'Final decision',
			reference_code: 'FINAL_DECISION_MOTOR',
			position: { x: 1200, y: 80 }
		},
		{ node_key: 'end', node_type: 'END', position: { x: 1440, y: 80 } }
	],
	edges: [
		{ from: 'start', to: 'validation' },
		{ from: 'validation', to: 'calculation' },
		{ from: 'calculation', to: 'affordability' },
		{ from: 'affordability', to: 'score' },
		{ from: 'score', to: 'final' },
		{ from: 'final', to: 'end' }
	]
};

test('grid, canvas, maker-checker governance, decision, and trace form one journey', async ({
	page,
	request
}) => {
	const suffix = Date.now().toString(36).toUpperCase();
	const segment = `E2E_${suffix}`;
	const analyst = await token(request, 'riskanalyst');
	const manager = await token(request, 'riskmanager');
	const los = await token(request, 'los-client');

	const tables = await api<Array<{ id: string; code: string }>>(
		request,
		'get',
		'/v1/decision-tables',
		analyst
	);
	const finalTable = tables.find((table) => table.code === 'FINAL_DECISION_MOTOR');
	expect(finalTable).toBeTruthy();

	const strategy = await api<{ id: string }>(request, 'post', '/v1/strategies', analyst, {
		strategy_code: `E2E_FLOW_${suffix}`,
		name: `E2E flow ${suffix}`,
		product_type: 'MOTOR_LEASEBACK',
		segment
	});
	const version = await api<{ id: string }>(
		request,
		'post',
		`/v1/strategies/${strategy.id}/versions`,
		analyst,
		{
			version_note: 'Playwright Phase 3 journey',
			graph
		}
	);
	const payload = applicationPayload(segment);
	const simulation = await api<{ simulation_id: string }>(
		request,
		'post',
		'/v1/simulations/single',
		analyst,
		{
			application_payload: payload,
			strategy_version_id: version.id
		}
	);
	await api(
		request,
		'post',
		`/v1/strategies/${strategy.id}/versions/${version.id}/submit-approval`,
		analyst,
		{ simulation_id: simulation.simulation_id }
	);
	await api(
		request,
		'post',
		`/v1/strategies/${strategy.id}/versions/${version.id}/activate`,
		manager,
		{ reason: 'Phase 3 E2E approval' }
	);
	const decision = await api<{ decision_id: string }>(
		request,
		'post',
		'/v1/decisions',
		los,
		payload
	);

	await login(page, 'riskanalyst');
	await page.goto(`/decision-tables/${finalTable.id}`);
	await expect(page.getByTestId('decision-table-grid')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'FINAL_DECISION_MOTOR' })).toBeVisible();

	await page.goto(`/strategies/${strategy.id}`);
	await expect(page.getByTestId('strategy-flow-canvas')).toBeVisible();
	await expect(page.getByText('ACTIVE', { exact: true }).first()).toBeVisible();

	await page.goto(`/decisions/${decision.decision_id}`);
	await expect(page.getByTestId('decision-summary')).toBeVisible();
	await expect(page.getByTestId('trace-steps')).toContainText('final');
	await expect(page.getByText('View executed flow')).toBeVisible();
});
