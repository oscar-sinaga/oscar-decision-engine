<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import type { BatchSimulationResponse, Strategy, StrategyVersion } from '$lib/api/types';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { formatPercent } from '$lib/format';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import { Button } from '$lib/components/ui/button';

	const SAMPLE_POPULATION = [
		{
			application_id: 'APP-BATCH-1',
			product_type: 'MOTOR_LEASEBACK',
			channel: 'BRANCH',
			applicant: {
				customer_id: 'C1',
				age: 34,
				monthly_income: 8500000,
				existing_monthly_obligation: 2500000
			},
			loan: { requested_amount: 15000000, requested_tenor_months: 24 },
			vehicle: { type: 'MOTOR', year: 2020, appraisal_value: 18000000 },
			fraud: { identity_match: true, document_match: true, blacklist_hit: false },
			model_outputs: { credit_score: 684, model_version: 'MOTOR_SCORE_V1' }
		},
		{
			application_id: 'APP-BATCH-2',
			product_type: 'MOTOR_LEASEBACK',
			channel: 'DEALER',
			applicant: {
				customer_id: 'C2',
				age: 41,
				monthly_income: 4000000,
				existing_monthly_obligation: 1500000
			},
			loan: { requested_amount: 20000000, requested_tenor_months: 24 },
			vehicle: { type: 'MOTOR', year: 2015, appraisal_value: 16000000 },
			fraud: { identity_match: true, document_match: true, blacklist_hit: false },
			model_outputs: { credit_score: 520, model_version: 'MOTOR_SCORE_V1' }
		}
	];

	let versions = $state<{ label: string; id: string }[]>([]);
	let simulationName = $state('');
	let strategyVersionId = $state('');
	let compare = $state(true);
	let payloadText = $state(JSON.stringify(SAMPLE_POPULATION, null, 2));
	let result = $state<BatchSimulationResponse | null>(null);
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
			result = await api<BatchSimulationResponse>('/v1/simulations/batch', {
				body: {
					simulation_name: simulationName,
					strategy_version_id: strategyVersionId,
					application_payloads: JSON.parse(payloadText),
					compare_with_active: compare
				}
			});
		} catch (err) {
			error = err instanceof ApiError ? err : new Error('Invalid JSON population');
		} finally {
			running = false;
		}
	}
</script>

{#snippet actions()}<Button href="/simulations" variant="outline" size="sm"
		>Single simulation</Button
	>{/snippet}
<PageHeader
	title="Simulations"
	description="Compare a candidate strategy against the active policy across a population."
	{actions}
/>
<div class="mb-4 inline-flex rounded-control border border-border bg-surface p-1">
	<a
		class="rounded-control px-3 py-1.5 text-xs font-medium text-text-muted hover:bg-surface-sunken"
		href="/simulations">Single</a
	>
	<a
		class="rounded-control bg-primary-50 px-3 py-1.5 text-xs font-semibold text-primary-700"
		href="/simulations/batch">Batch</a
	>
</div>

<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
	<div class="space-y-4">
		<Card title="Population (JSON array of application payloads)">
			<textarea
				class="h-96 w-full rounded border-slate-300 font-mono text-xs"
				bind:value={payloadText}
				data-testid="batch-payload"></textarea>
		</Card>
		<Card title="Run configuration">
			<div class="space-y-3 text-xs font-semibold text-slate-600">
				<label class="block">
					Simulation name
					<input class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={simulationName} />
				</label>
				<label class="block">
					Candidate strategy version
					<select
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={strategyVersionId}
					>
						<option value="">— select a version —</option>
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
					disabled={running || !strategyVersionId}
					data-testid="run-batch"
				>
					{running ? 'Running…' : 'Run policy impact analysis'}
				</button>
			</div>
			{#if error}
				<div class="mt-3"><ErrorNote {error} /></div>
			{/if}
		</Card>
	</div>

	<div class="space-y-4">
		{#if result}
			<Card title="Impact — {result.total_records} records">
				<div class="grid grid-cols-1 gap-3 md:grid-cols-2" data-testid="batch-result">
					{#snippet aggregate(title: string, agg: BatchSimulationResponse['target'])}
						<div class="rounded border border-slate-200 p-3">
							<h3 class="mb-1 text-xs font-semibold text-slate-500 uppercase">{title}</h3>
							<p class="text-[11px] text-slate-500">{agg.strategy_version}</p>
							<dl class="mt-2 space-y-1 text-sm">
								<div class="flex justify-between">
									<dt class="text-slate-500">Approval</dt>
									<dd class="font-semibold text-emerald-700">{formatPercent(agg.approval_rate)}</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-slate-500">Reject</dt>
									<dd class="font-semibold text-red-700">{formatPercent(agg.reject_rate)}</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-slate-500">Manual review</dt>
									<dd class="font-semibold text-amber-700">
										{formatPercent(agg.manual_review_rate)}
									</dd>
								</div>
							</dl>
						</div>
					{/snippet}
					{@render aggregate('Candidate', result.target)}
					{#if result.active}
						{@render aggregate('Active', result.active)}
					{/if}
				</div>

				{#if result.decision_shifts.length > 0}
					<h3 class="mt-4 mb-1 text-xs font-semibold text-slate-500 uppercase">
						Decision shifts (active → candidate)
					</h3>
					<table class="w-full text-xs">
						<tbody>
							{#each result.decision_shifts as shift (shift.from_decision + shift.to_decision)}
								<tr class="border-t border-slate-100">
									<td class="py-1">{shift.from_decision.replaceAll('_', ' ')}</td>
									<td class="py-1 text-center text-slate-400">→</td>
									<td class="py-1">{shift.to_decision.replaceAll('_', ' ')}</td>
									<td class="py-1 text-right font-semibold">{shift.count}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</Card>

			<Card title="Top reason codes (candidate)">
				{#if Object.keys(result.target.reason_code_distribution).length === 0}
					<p class="text-sm text-slate-500">No reason codes.</p>
				{:else}
					<ul class="space-y-1 text-sm">
						{#each Object.entries(result.target.reason_code_distribution) as [code, count] (code)}
							<li class="flex justify-between">
								<span class="font-mono text-xs">{code}</span><span class="font-semibold"
									>{count}</span
								>
							</li>
						{/each}
					</ul>
				{/if}
			</Card>

			<Card title="Segment impact">
				<table class="w-full text-xs" data-testid="segment-impact">
					<thead class="text-left text-slate-400">
						<tr
							><th class="py-1">Segment</th><th class="py-1">Records</th><th class="py-1"
								>Candidate decisions</th
							></tr
						>
					</thead>
					<tbody>
						{#each result.segment_impact as seg (seg.segment)}
							<tr class="border-t border-slate-100">
								<td class="py-1 font-mono">{seg.segment}</td>
								<td class="py-1">{seg.total}</td>
								<td class="py-1 font-mono text-[11px]">
									{Object.entries(seg.target_decision_counts)
										.map(([d, c]) => `${d}:${c}`)
										.join('  ')}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</Card>
		{:else}
			<Card title="Impact">
				<p class="text-sm text-slate-500">
					Select a candidate strategy version and run to see the population-level impact.
				</p>
			</Card>
		{/if}
	</div>
</div>
