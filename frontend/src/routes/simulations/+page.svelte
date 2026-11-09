<script lang="ts">
	import { appPath } from '$lib/app-path';

	import { api, ApiError } from '$lib/api/client';
	import type { SimulationResponse, Strategy, StrategyVersion } from '$lib/api/types';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import EmptyState from '$lib/ui/EmptyState.svelte';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';

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
			toast.success('Simulation completed');
		} catch (err) {
			error = err instanceof ApiError ? err : new Error('Invalid JSON payload');
			toast.error(err instanceof ApiError ? err.message : 'Simulation failed');
		} finally {
			running = false;
		}
	}
</script>

{#snippet actions()}<Button href={appPath(`/simulations/batch`)} variant="outline" size="sm"
		>Batch simulation</Button
	>{/snippet}
<PageHeader
	title="Simulations"
	description="Run the decision engine without creating production decisions."
	{actions}
/>
<nav
	class="mb-4 inline-flex rounded-control border border-border bg-surface p-1"
	aria-label="Simulation type"
>
	<a
		class="rounded-control bg-primary-50 px-3 py-1.5 text-xs font-semibold text-primary-700"
		href={appPath(`/simulations`)}>Single</a
	><a
		class="rounded-control px-3 py-1.5 text-xs font-medium text-text-muted hover:bg-surface-sunken"
		href={appPath(`/simulations/batch`)}>Batch</a
	>
</nav>

<div class="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
	<div class="space-y-4">
		<section class="rounded-card border border-border bg-surface p-4 shadow-card">
			<div class="mb-2 flex items-center justify-between">
				<h2 class="text-sm font-semibold text-text">Application payload</h2>
				<span class="font-mono text-[10px] text-text-faint">JSON</span>
			</div>
			<textarea
				class="h-[30rem] w-full rounded-control border border-border bg-surface-sunken p-3 font-mono text-xs text-text focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
				bind:value={payloadText}
				data-testid="sim-payload"></textarea>
			<p class="mt-2 text-[11px] text-text-muted">
				Payload is validated by the same engine schema used by production decisions.
			</p>
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
					>Strategy version<select
						class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-3 text-sm text-text"
						bind:value={strategyVersionId}
						><option value="">Active strategy for payload product/segment</option
						>{#each versions as version (version.id)}<option value={version.id}
								>{version.label}</option
							>{/each}</select
					></label
				><label class="flex items-center gap-2 text-xs font-medium text-text-muted"
					><input type="checkbox" bind:checked={compare} />Compare with active strategy</label
				><button
					class="rounded-control bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
					onclick={run}
					disabled={running}
					data-testid="run-simulation">{running ? 'Running…' : 'Run simulation'}</button
				>
			</div>
			{#if error}<div class="mt-3"><ErrorNote {error} /></div>{/if}
		</section>
	</div>
	<div class="space-y-4">
		{#if result}
			<section
				class="rounded-card border border-border bg-surface p-5 shadow-card"
				data-testid="sim-result"
			>
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<p class="font-mono text-[11px] text-text-muted">{result.simulation_id}</p>
						<h2 class="mt-1 text-sm font-semibold text-text">Simulation outcome</h2>
					</div>
					<StatusBadge value={result.mode} />
				</div>
				<div class="mt-5 grid gap-3 md:grid-cols-2">
					<article class="rounded-card border border-primary-500/20 bg-primary-50/50 p-4">
						<p class="text-xs font-semibold uppercase tracking-wide text-text-muted">
							Target · {result.draft_result.strategy_version}
						</p>
						<div class="mt-3">
							<StatusBadge value={result.draft_result.decision} />
						</div>
						<div class="mt-3 flex flex-wrap gap-1">
							{#each result.draft_result.reason_codes as code (code)}<span
									class="rounded-control bg-surface px-2 py-1 font-mono text-[10px] text-text"
									>{code}</span
								>{:else}<span class="text-xs text-text-muted">No reason codes.</span>{/each}
						</div>
					</article>
					{#if result.active_result}<article
							class="rounded-card border border-border bg-surface-muted p-4"
						>
							<p class="text-xs font-semibold uppercase tracking-wide text-text-muted">
								Active · {result.active_result.strategy_version}
							</p>
							<div class="mt-3">
								<StatusBadge value={result.active_result.decision} />
							</div>
							<div class="mt-3 flex flex-wrap gap-1">
								{#each result.active_result.reason_codes as code (code)}<span
										class="rounded-control bg-surface px-2 py-1 font-mono text-[10px] text-text"
										>{code}</span
									>{:else}<span class="text-xs text-text-muted">No reason codes.</span>{/each}
							</div>
						</article>{/if}
				</div>
				{#if result.differences.length}<div
						class="mt-5 overflow-hidden rounded-card border border-border"
					>
						<table class="w-full text-xs">
							<thead class="bg-surface-sunken text-left text-text-muted"
								><tr
									><th scope="col" class="px-3 py-2">Field</th><th scope="col" class="px-3 py-2"
										>Active</th
									><th scope="col" class="px-3 py-2">Target</th></tr
								></thead
							><tbody
								>{#each result.differences as diff (diff.field)}<tr class="border-t border-border"
										><td class="px-3 py-2 font-semibold text-text">{diff.field}</td><td
											class="px-3 py-2 font-mono text-[11px] text-text-muted"
											>{JSON.stringify(diff.active)}</td
										><td class="px-3 py-2 font-mono text-[11px] text-text"
											>{JSON.stringify(diff.draft)}</td
										></tr
									>{/each}</tbody
							>
						</table>
					</div>{:else if result.active_result}<p
						class="mt-4 rounded-control bg-success-bg p-3 text-xs text-success"
					>
						No differences between active and target version.
					</p>{/if}
			</section>
			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<h2 class="mb-3 text-sm font-semibold text-text">Full outcome</h2>
				<JsonBlock value={result} maxHeight="24rem" />
			</section>
		{:else}<section class="rounded-card border border-border bg-surface p-8 shadow-card">
				<EmptyState
					title="No simulation result"
					hint="Configure the payload and run a simulation to inspect the outcome."
				/>
			</section>{/if}
	</div>
</div>
