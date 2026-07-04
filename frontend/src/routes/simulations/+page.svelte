<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import type { SimulationResponse, Strategy, StrategyVersion } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';

	const SAMPLE_PAYLOAD = {
		application_id: 'APP-SIM-0001',
		product_type: 'MOTOR_LEASEBACK',
		channel: 'BRANCH',
		applicant: {
			customer_id: 'CUST-SIM-001',
			age: 34,
			employment_type: 'EMPLOYEE',
			monthly_income: 8500000,
			existing_monthly_obligation: 2500000
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

	let versions = $state<{ label: string; id: string }[]>([]);
	let simulationName = $state('');
	let payloadText = $state(JSON.stringify(SAMPLE_PAYLOAD, null, 2));
	let strategyVersionId = $state('');
	let compare = $state(true);
	let result = $state<SimulationResponse | null>(null);
	let error = $state<unknown>(null);
	let running = $state(false);

	$effect(() => {
		api<Strategy[]>('/v1/strategies')
			.then(async (list) => {
				const all: { label: string; id: string }[] = [];
				for (const strategy of list) {
					const detail = await api<Strategy>(`/v1/strategies/${strategy.id}`);
					for (const version of (detail.versions ?? []) as StrategyVersion[]) {
						all.push({
							label: `${strategy.strategy_code} v${version.version} (${version.status})`,
							id: version.id
						});
					}
				}
				versions = all;
			})
			.catch(() => {});
	});

	async function run() {
		error = null;
		result = null;
		running = true;
		try {
			result = await api<SimulationResponse>('/v1/simulations/single', {
				body: {
					simulation_name: simulationName,
					application_payload: JSON.parse(payloadText),
					strategy_version_id: strategyVersionId || null,
					compare_with_active: compare
				}
			});
		} catch (err) {
			error = err instanceof ApiError ? err : new Error('Invalid JSON payload');
		} finally {
			running = false;
		}
	}
</script>

<h1 class="mb-1 text-xl font-bold text-slate-800">Single Application Simulator</h1>
<p class="mb-4 text-sm text-slate-500">
	Runs the decision engine without creating any production decision (mode SIMULATION).
</p>

<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
	<div class="space-y-4">
		<Card title="Application payload">
			<textarea
				class="h-96 w-full rounded border-slate-300 font-mono text-xs"
				bind:value={payloadText}
				data-testid="sim-payload"></textarea>
		</Card>

		<Card title="Run configuration">
			<div class="space-y-3 text-xs font-semibold text-slate-600">
				<label class="block">
					Simulation name
					<input class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={simulationName} />
				</label>
				<label class="block">
					Strategy version (empty = active strategy)
					<select
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={strategyVersionId}
					>
						<option value="">Active strategy for payload product/segment</option>
						{#each versions as version (version.id)}
							<option value={version.id}>{version.label}</option>
						{/each}
					</select>
				</label>
				<label class="flex items-center gap-2">
					<input type="checkbox" class="rounded border-slate-300" bind:checked={compare} />
					Compare with active strategy
				</label>
				<button
					class="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
					onclick={run}
					disabled={running}
					data-testid="run-simulation"
				>
					{running ? 'Running…' : 'Run simulation'}
				</button>
			</div>
			{#if error}
				<div class="mt-3"><ErrorNote {error} /></div>
			{/if}
		</Card>
	</div>

	<div class="space-y-4">
		{#if result}
			<Card title="Result — {result.simulation_id}">
				{#snippet actions()}<Badge value={result?.mode ?? 'SIMULATION'} />{/snippet}
				<div class="grid grid-cols-1 gap-3 md:grid-cols-2" data-testid="sim-result">
					<div class="rounded border border-slate-200 p-3">
						<h3 class="mb-1 text-xs font-semibold text-slate-500 uppercase">
							Target ({result.draft_result.strategy_version})
						</h3>
						<Badge value={result.draft_result.decision} kind="decision" />
						<p class="mt-2 font-mono text-[11px] text-slate-500">
							{result.draft_result.reason_codes.join(', ') || 'no reason codes'}
						</p>
					</div>
					{#if result.active_result}
						<div class="rounded border border-slate-200 p-3">
							<h3 class="mb-1 text-xs font-semibold text-slate-500 uppercase">
								Active ({result.active_result.strategy_version})
							</h3>
							<Badge value={result.active_result.decision} kind="decision" />
							<p class="mt-2 font-mono text-[11px] text-slate-500">
								{result.active_result.reason_codes.join(', ') || 'no reason codes'}
							</p>
						</div>
					{/if}
				</div>

				{#if result.differences.length > 0}
					<h3 class="mt-4 mb-1 text-xs font-semibold text-slate-500 uppercase">Differences</h3>
					<table class="w-full text-xs">
						<thead class="text-left text-slate-400">
							<tr
								><th class="py-1">Field</th><th class="py-1">Active</th><th class="py-1">Draft</th
								></tr
							>
						</thead>
						<tbody>
							{#each result.differences as diff (diff.field)}
								<tr class="border-t border-slate-100">
									<td class="py-1 font-semibold">{diff.field}</td>
									<td class="py-1 font-mono">{JSON.stringify(diff.active)}</td>
									<td class="py-1 font-mono">{JSON.stringify(diff.draft)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else if result.active_result}
					<p class="mt-3 text-xs text-slate-500">
						No differences between active and target version.
					</p>
				{/if}
			</Card>

			<Card title="Full outcome">
				<JsonBlock value={result} maxHeight="24rem" />
			</Card>
		{:else}
			<Card title="Result">
				<p class="text-sm text-slate-500">Run a simulation to see the outcome and rule hits.</p>
			</Card>
		{/if}
	</div>
</div>
