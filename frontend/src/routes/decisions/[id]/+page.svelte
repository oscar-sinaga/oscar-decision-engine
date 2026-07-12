<script lang="ts">
	import { page } from '$app/state';
	import { ArrowLeft, ExternalLink } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { DecisionResponse, TraceResponse } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Tabs from '$lib/components/ui/tabs';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import { formatCurrency, formatPercent } from '$lib/format';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import TraceTimeline from '$lib/ui/TraceTimeline.svelte';
	import { setBreadcrumb } from '$lib/ui/breadcrumb.svelte';

	let decision = $state<DecisionResponse | null>(null);
	let trace = $state<TraceResponse | null>(null);
	let error = $state<unknown>(null);
	let traceError = $state<unknown>(null);
	let tab = $state('timeline');

	$effect(() => {
		const id = page.params.id;
		api<DecisionResponse>(`/v1/decisions/${id}`)
			.then((value) => {
				decision = value;
				setBreadcrumb(value.application_id);
			})
			.catch((err) => (error = err));
		api<TraceResponse>(`/v1/decisions/${id}/trace`)
			.then((value) => (trace = value))
			.catch((err) => (traceError = err));
	});
</script>

{#snippet actions()}
	<Button href="/decisions" variant="outline" size="sm"
		><ArrowLeft size={15} /> Back to decisions</Button
	>
{/snippet}

{#if error}
	<ErrorNote {error} />
{:else if decision}
	<PageHeader
		title={decision.application_id}
		description={`Decision ${decision.decision_id}`}
		{actions}
	/>
	<div class="mb-4 flex flex-wrap items-center gap-2">
		<StatusBadge value={decision.decision} class="text-xs" />
		<StatusBadge value={decision.execution_mode} />
		{#if decision.created_at}<RelativeTime value={decision.created_at} />{/if}
	</div>

	<div class="grid gap-4 xl:grid-cols-3" data-testid="decision-summary">
		<Card.Root>
			<Card.Header><Card.Title>Decision & reasons</Card.Title></Card.Header>
			<Card.Content>
				<div class="mb-4 flex items-center justify-between">
					<StatusBadge value={decision.decision} class="text-xs" /><span
						class="font-mono text-sm font-semibold">{decision.risk_grade ?? '—'}</span
					>
				</div>
				{#if decision.reason_codes.length}
					<ul class="space-y-2">
						{#each decision.reason_codes as reason (reason.code)}<li
								class="rounded-control bg-surface-muted px-3 py-2"
							>
								<span class="font-mono text-xs font-semibold">{reason.code}</span>
								<p class="mt-0.5 text-xs text-text-muted">{reason.message}</p>
							</li>{/each}
					</ul>
				{:else}<p class="text-sm text-text-muted">No reason codes.</p>{/if}
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header><Card.Title>Application snapshot</Card.Title></Card.Header>
			<Card.Content>
				<dl class="space-y-2 text-sm">
					<div class="flex justify-between gap-4">
						<dt class="text-text-muted">Application</dt>
						<dd class="font-mono text-xs">{decision.application_id}</dd>
					</div>
					<div class="flex justify-between gap-4">
						<dt class="text-text-muted">Score</dt>
						<dd class="tabular-nums">{decision.score ?? '—'}</dd>
					</div>
					<div class="flex justify-between gap-4">
						<dt class="text-text-muted">Approved limit</dt>
						<dd class="tabular-nums">{formatCurrency(decision.approved_limit)}</dd>
					</div>
					<div class="flex justify-between gap-4">
						<dt class="text-text-muted">Tenor</dt>
						<dd class="tabular-nums">
							{decision.approved_tenor_months ? `${decision.approved_tenor_months} months` : '—'}
						</dd>
					</div>
					<div class="flex justify-between gap-4">
						<dt class="text-text-muted">Pricing</dt>
						<dd class="tabular-nums">
							{decision.pricing_rate !== null ? formatPercent(decision.pricing_rate, 2) : '—'}
						</dd>
					</div>
					{#if decision.manual_review_case_id}<div class="flex justify-between gap-4">
							<dt class="text-text-muted">Review case</dt>
							<dd>
								<a
									class="font-mono text-xs text-primary-700 hover:underline"
									href={`/manual-review/${decision.manual_review_case_id}`}
									>{decision.manual_review_case_id}</a
								>
							</dd>
						</div>{/if}
				</dl>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header><Card.Title>Runtime</Card.Title></Card.Header>
			<Card.Content>
				{#if trace}
					<dl class="space-y-2 text-sm">
						<div class="flex justify-between gap-4">
							<dt class="text-text-muted">Strategy version</dt>
							<dd class="font-mono text-xs">
								{trace.strategy.strategy_code} v{trace.strategy.version}
							</dd>
						</div>
						<div class="flex justify-between gap-4">
							<dt class="text-text-muted">Latency</dt>
							<dd class="font-mono text-xs tabular-nums">{trace.metadata.latency_ms} ms</dd>
						</div>
						<div>
							<dt class="text-text-muted">Trace ID</dt>
							<dd class="mt-1 break-all font-mono text-[10px]">{trace.trace_id}</dd>
						</div>
						<div>
							<dt class="text-text-muted">Correlation ID</dt>
							<dd class="mt-1 break-all font-mono text-[10px]">
								{trace.metadata.correlation_id ?? '—'}
							</dd>
						</div>
					</dl>
				{:else if traceError}<ErrorNote error={traceError} />{:else}<div class="space-y-3">
						<Skeleton class="h-4 w-full" /><Skeleton class="h-4 w-4/5" /><Skeleton
							class="h-4 w-full"
						/>
					</div>{/if}
			</Card.Content>
		</Card.Root>
	</div>

	{#if trace}
		<div class="mt-4">
			<Tabs.Root bind:value={tab}>
				<div class="mb-3 flex flex-wrap items-center justify-between gap-3">
					<Tabs.List variant="line"
						><Tabs.Trigger value="timeline">Execution trace</Tabs.Trigger><Tabs.Trigger
							value="outputs">Outputs</Tabs.Trigger
						><Tabs.Trigger value="features">Calculated features</Tabs.Trigger><Tabs.Trigger
							value="raw">Raw trace</Tabs.Trigger
						></Tabs.List
					>
					{#if trace.strategy.strategy_id}<Button
							variant="outline"
							size="sm"
							href={`/strategies/${trace.strategy.strategy_id}?version=${trace.strategy.version_id ?? ''}`}
							>View executed flow <ExternalLink size={14} /></Button
						>{/if}
				</div>
				<Tabs.Content value="timeline"
					><Card.Root
						><Card.Header
							><Card.Title>{trace.strategy.strategy_code} v{trace.strategy.version}</Card.Title
							><Card.Description
								>Deterministic path and duration for each executed graph node.</Card.Description
							></Card.Header
						><Card.Content><TraceTimeline steps={trace.steps} /></Card.Content></Card.Root
					></Tabs.Content
				>
				<Tabs.Content value="outputs"
					><Card.Root
						><Card.Header><Card.Title>Outputs</Card.Title></Card.Header><Card.Content
							><JsonBlock value={trace.outputs} maxHeight="32rem" /></Card.Content
						></Card.Root
					></Tabs.Content
				>
				<Tabs.Content value="features"
					><Card.Root
						><Card.Header><Card.Title>Calculated features</Card.Title></Card.Header><Card.Content
							><JsonBlock value={trace.feature_values} maxHeight="32rem" /></Card.Content
						></Card.Root
					></Tabs.Content
				>
				<Tabs.Content value="raw"
					><Card.Root
						><Card.Header><Card.Title>Raw trace for auditors</Card.Title></Card.Header><Card.Content
							><JsonBlock value={trace} maxHeight="40rem" /></Card.Content
						></Card.Root
					></Tabs.Content
				>
			</Tabs.Root>
		</div>
	{/if}
{:else}
	<div class="space-y-4">
		<Skeleton class="h-10 w-72" />
		<div class="grid gap-4 xl:grid-cols-3">
			<Skeleton class="h-64" /><Skeleton class="h-64" /><Skeleton class="h-64" />
		</div>
	</div>
{/if}
