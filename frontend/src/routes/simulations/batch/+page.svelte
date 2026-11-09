<script lang="ts">
	import { appPath } from '$lib/app-path';

	import { api, ApiError } from '$lib/api/client';
	import type { BatchSimulationResponse, Strategy, StrategyVersion } from '$lib/api/types';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { formatPercent } from '$lib/format';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import { toast } from 'svelte-sonner';
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
			toast.success('Policy impact analysis completed');
		} catch (err) {
			error = err instanceof ApiError ? err : new Error('Invalid JSON population');
			toast.error(err instanceof ApiError ? err.message : 'Policy impact analysis failed');
		} finally {
			running = false;
		}
	}
</script>

{#snippet actions()}<Button href={appPath(`/simulations`)} variant="outline" size="sm"
		>Single simulation</Button
	>{/snippet}
<PageHeader
	title="Simulations"
	description="Compare a candidate strategy against the active policy across a population."
	{actions}
/>
<nav
	class="mb-4 inline-flex rounded-control border border-border bg-surface p-1"
	aria-label="Simulation type"
>
	<a
		class="rounded-control px-3 py-1.5 text-xs font-medium text-text-muted hover:bg-surface-sunken"
		href={appPath(`/simulations`)}>Single</a
	><a
		class="rounded-control bg-primary-50 px-3 py-1.5 text-xs font-semibold text-primary-700"
		href={appPath(`/simulations/batch`)}>Batch</a
	>
</nav>
<div class="grid gap-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
	<div class="space-y-4">
		<section class="rounded-card border border-border bg-surface p-4 shadow-card">
			<div class="mb-2 flex items-center justify-between">
				<h2 class="text-sm font-semibold text-text">Population</h2>
				<span class="font-mono text-[10px] text-text-faint">JSON array</span>
			</div>
			<textarea
				class="h-[30rem] w-full rounded-control border border-border bg-surface-sunken p-3 font-mono text-xs text-text"
				bind:value={payloadText}
				data-testid="batch-payload"></textarea>
		</section>
		<section class="rounded-card border border-border bg-surface p-4 shadow-card">
			<h2 class="mb-3 text-sm font-semibold text-text">Run configuration</h2>
			<div class="space-y-3">
				<label class="block text-xs font-medium text-text-muted"
					>Simulation name<input
						class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-3 text-sm text-text"
						bind:value={simulationName}
					/></label
				><label class="block text-xs font-medium text-text-muted"
					>Candidate strategy version<select
						class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-3 text-sm text-text"
						bind:value={strategyVersionId}
						><option value="">— select a version —</option
						>{#each versions as version (version.id)}<option value={version.id}
								>{version.label}</option
							>{/each}</select
					></label
				><label class="flex items-center gap-2 text-xs font-medium text-text-muted"
					><input type="checkbox" bind:checked={compare} />Compare with active strategy</label
				><button
					class="rounded-control bg-primary-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
					onclick={run}
					disabled={running || !strategyVersionId}
					data-testid="run-batch">{running ? 'Running…' : 'Run policy impact analysis'}</button
				>
			</div>
			{#if error}<div class="mt-3"><ErrorNote {error} /></div>{/if}
		</section>
	</div>
	<div class="space-y-4">
		{#if result}<section
				class="rounded-card border border-border bg-surface p-5 shadow-card"
				data-testid="batch-result"
			>
				<div class="flex items-center justify-between">
					<div>
						<p class="font-mono text-[11px] text-text-muted">{result.simulation_id}</p>
						<h2 class="text-sm font-semibold text-text">Impact · {result.total_records} records</h2>
					</div>
				</div>
				<div class="mt-4 grid gap-3 md:grid-cols-2">
					{#snippet aggregate(title: string, agg: BatchSimulationResponse['target'])}<article
							class="rounded-card border border-border bg-surface-muted p-4"
						>
							<p class="text-xs font-semibold uppercase tracking-wide text-text-muted">{title}</p>
							<p class="mt-1 font-mono text-[11px] text-text-faint">{agg.strategy_version}</p>
							<dl class="mt-3 space-y-2 text-sm">
								<div class="flex justify-between">
									<dt class="text-text-muted">Approval</dt>
									<dd class="font-semibold text-success">{formatPercent(agg.approval_rate)}</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-text-muted">Reject</dt>
									<dd class="font-semibold text-danger">{formatPercent(agg.reject_rate)}</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-text-muted">Manual review</dt>
									<dd class="font-semibold text-warning">
										{formatPercent(agg.manual_review_rate)}
									</dd>
								</div>
							</dl>
						</article>{/snippet}{@render aggregate(
						'Candidate',
						result.target
					)}{#if result.active}{@render aggregate('Active', result.active)}{/if}
				</div>
				{#if result.decision_shifts.length}<div
						class="mt-5 overflow-hidden rounded-card border border-border"
					>
						<table class="w-full text-xs">
							<thead class="bg-surface-sunken text-left text-text-muted"
								><tr
									><th scope="col" class="px-3 py-2">From</th><th scope="col" class="px-3 py-2"
										>To</th
									><th scope="col" class="px-3 py-2 text-right">Count</th></tr
								></thead
							><tbody
								>{#each result.decision_shifts as shift (shift.from_decision + shift.to_decision)}<tr
										class="border-t border-border"
										><td class="px-3 py-2">{shift.from_decision.replaceAll('_', ' ')}</td><td
											class="px-3 py-2">→ {shift.to_decision.replaceAll('_', ' ')}</td
										><td class="px-3 py-2 text-right font-semibold">{shift.count}</td></tr
									>{/each}</tbody
							>
						</table>
					</div>{/if}
			</section>
			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<h2 class="mb-3 text-sm font-semibold text-text">Top reason codes</h2>
				{#if Object.keys(result.target.reason_code_distribution).length}<ul class="space-y-2">
						{#each Object.entries(result.target.reason_code_distribution) as [code, count] (code)}<li
								class="flex justify-between rounded-control bg-surface-muted px-3 py-2"
							>
								<span class="font-mono text-xs text-text">{code}</span><span
									class="font-semibold text-text">{count}</span
								>
							</li>{/each}
					</ul>{:else}<p class="text-sm text-text-muted">No reason codes.</p>{/if}
			</section>
			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<h2 class="mb-3 text-sm font-semibold text-text">Segment impact</h2>
				<div class="overflow-auto">
					<table class="w-full text-xs" data-testid="segment-impact">
						<thead class="bg-surface-sunken text-left text-text-muted"
							><tr
								><th scope="col" class="px-3 py-2">Segment</th><th scope="col" class="px-3 py-2"
									>Records</th
								><th scope="col" class="px-3 py-2">Candidate decisions</th></tr
							></thead
						><tbody
							>{#each result.segment_impact as seg (seg.segment)}<tr class="border-t border-border"
									><td class="px-3 py-2 font-mono">{seg.segment}</td><td class="px-3 py-2"
										>{seg.total}</td
									><td class="px-3 py-2 font-mono text-[11px]"
										>{Object.entries(seg.target_decision_counts)
											.map(([d, c]) => `${d}:${c}`)
											.join('  ')}</td
									></tr
								>{/each}</tbody
						>
					</table>
				</div>
			</section>{:else}<section
				class="rounded-card border border-border bg-surface p-8 shadow-card"
			>
				<EmptyState
					title="No policy impact result"
					hint="Select a candidate version and run the population comparison."
				/>
			</section>{/if}
	</div>
</div>
