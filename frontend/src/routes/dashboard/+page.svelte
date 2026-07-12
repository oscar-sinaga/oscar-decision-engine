<script lang="ts">
	import { goto } from '$app/navigation';
	import { ArrowRight, Search } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type {
		DecisionHistoryItem,
		DecisionSummary,
		DecisionTrend,
		Meta,
		Page
	} from '$lib/api/types';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { formatPercent } from '$lib/format';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import FilterBar from '$lib/ui/FilterBar.svelte';
	import KpiCard from '$lib/ui/KpiCard.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	type RecentRow = DecisionHistoryItem & Record<string, unknown>;
	let summary = $state<DecisionSummary | null>(null);
	let trend = $state<DecisionTrend | null>(null);
	let recent = $state<DecisionHistoryItem[]>([]);
	let meta = $state<Meta | null>(null);
	let summaryError = $state<unknown>(null);
	let trendError = $state<unknown>(null);
	let recentError = $state<unknown>(null);
	let productType = $state('');
	let channel = $state('');
	let loadingSummary = $state(true);
	let loadingTrend = $state(true);
	let loadingRecent = $state(true);

	const maxBucket = $derived(Math.max(1, ...(trend?.buckets ?? []).map((bucket) => bucket.total)));
	const decisionTotal = $derived(
		Object.values(summary?.decision_counts ?? {}).reduce((total, count) => total + count, 0)
	);
	const maxReason = $derived(
		Math.max(1, ...(summary?.top_reason_codes ?? []).map((item) => item.count))
	);
	const gradeCounts = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const item of recent) {
			const grade = item.risk_grade ?? 'UNCLASSIFIED';
			counts[grade] = (counts[grade] ?? 0) + 1;
		}
		return Object.entries(counts).sort((a, b) => b[1] - a[1]);
	});
	const maxGrade = $derived(Math.max(1, ...gradeCounts.map(([, count]) => count)));
	const recentRows = $derived(recent.slice(0, 5) as RecentRow[]);

	async function loadSummary(): Promise<void> {
		summaryError = null;
		loadingSummary = true;
		try {
			summary = await api<DecisionSummary>('/v1/monitoring/decision-summary', {
				query: { product_type: productType || undefined, channel: channel || undefined }
			});
		} catch (err) {
			summaryError = err;
		} finally {
			loadingSummary = false;
		}
	}
	async function loadTrend(): Promise<void> {
		trendError = null;
		loadingTrend = true;
		try {
			trend = await api<DecisionTrend>('/v1/monitoring/decision-trend', {
				query: { product_type: productType || undefined, channel: channel || undefined }
			});
		} catch (err) {
			trendError = err;
		} finally {
			loadingTrend = false;
		}
	}
	async function loadRecent(): Promise<void> {
		recentError = null;
		loadingRecent = true;
		try {
			const page = await api<Page<DecisionHistoryItem>>('/v1/decisions', {
				query: {
					product_type: productType || undefined,
					channel: channel || undefined,
					page: 1,
					page_size: 5
				}
			});
			recent = page.items;
		} catch (err) {
			recentError = err;
		} finally {
			loadingRecent = false;
		}
	}
	async function load(): Promise<void> {
		await Promise.all([loadSummary(), loadTrend(), loadRecent()]);
	}
	$effect(() => {
		load();
		api<Meta>('/v1/meta')
			.then((value) => (meta = value))
			.catch(() => {});
	});
</script>

{#snippet recentDecision(row: RecentRow)}<StatusBadge value={row.decision} />{/snippet}
{#snippet recentApplication(row: RecentRow)}<span class="font-mono text-xs"
		>{row.application_id}</span
	>{/snippet}
{#snippet recentCreated(row: RecentRow)}<RelativeTime value={row.created_at} />{/snippet}
{#if true}
	{@const recentColumns: Column<RecentRow>[] = [
		{ key: 'application_id', header: 'Application', cell: recentApplication },
		{ key: 'decision', header: 'Decision', cell: recentDecision },
		{ key: 'risk_grade', header: 'Grade' },
		{ key: 'created_at', header: 'Created', cell: recentCreated }
	]}
	<PageHeader
		title="Dashboard"
		description="Current decision mix, policy signals, latency, and review workload."
	/>
	<FilterBar
		onReset={() => {
			productType = '';
			channel = '';
			load();
		}}
	>
		<label class="min-w-48 text-xs font-medium text-text-muted"
			>Product<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={productType}
				><option value="">All products</option
				>{#each meta?.product_types ?? [] as product (product)}<option value={product}
						>{product}</option
					>{/each}</select
			></label
		>
		<label class="min-w-44 text-xs font-medium text-text-muted"
			>Channel<Input class="mt-1" placeholder="e.g. BRANCH" bind:value={channel} /></label
		>
		<Button size="sm" onclick={load}><Search size={15} /> Apply</Button>
	</FilterBar>

	<div class="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-testid="kpi-cards">
		<KpiCard label="Decisions" value={summary?.total_applications ?? 0} loading={loadingSummary} />
		<KpiCard
			label="Approval rate"
			value={summary ? formatPercent(summary.approval_rate) : '—'}
			loading={loadingSummary}
		/>
		<KpiCard
			label="Manual review rate"
			value={summary ? formatPercent(summary.manual_review_rate) : '—'}
			loading={loadingSummary}
			deltaDirectionGood="down"
		/>
		<KpiCard
			label="Error rate"
			value={summary ? formatPercent(summary.error_rate) : '—'}
			loading={loadingSummary}
			deltaDirectionGood="down"
		/>
	</div>
	{#if summaryError}<div class="mb-4"><ErrorNote error={summaryError} /></div>{/if}

	<div class="grid gap-4 xl:grid-cols-2">
		<Card.Root>
			<Card.Header
				><Card.Title>Decision mix</Card.Title><Card.Description
					>Distribution for the active filter window.</Card.Description
				></Card.Header
			>
			<Card.Content>
				{#if loadingSummary}<Skeleton class="h-24 w-full" />{:else if summary && decisionTotal > 0}
					<div
						class="flex h-5 overflow-hidden rounded-full bg-surface-sunken"
						aria-label="Decision distribution"
					>
						{#each Object.entries(summary.decision_counts) as [decision, count] (decision)}
							<div
								class="h-full bg-primary-600 first:rounded-l-full last:rounded-r-full odd:bg-info even:bg-primary-600"
								style={`width:${(count / decisionTotal) * 100}%`}
								title={`${decision}: ${count}`}
							></div>
						{/each}
					</div>
					<div class="mt-4 grid gap-2 sm:grid-cols-2">
						{#each Object.entries(summary.decision_counts) as [decision, count] (decision)}
							<div class="flex items-center justify-between text-xs">
								<StatusBadge value={decision} /><span class="font-semibold tabular-nums"
									>{count}</span
								>
							</div>
						{/each}
					</div>
				{:else}<p class="text-sm text-text-muted">No decisions in this window.</p>{/if}
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header
				><Card.Title>Top reason codes</Card.Title><Card.Description
					>Most frequent policy explanations.</Card.Description
				></Card.Header
			>
			<Card.Content>
				{#if loadingSummary}<div class="space-y-3">
						{#each Array.from({ length: 5 }, (_, index) => index) as index (index)}<Skeleton
								class="h-5 w-full"
							/>{/each}
					</div>{:else if summary?.top_reason_codes.length}
					<ul class="space-y-3">
						{#each summary.top_reason_codes.slice(0, 5) as item (item.code)}<li>
								<div class="mb-1 flex justify-between text-xs">
									<span class="font-mono">{item.code}</span><span class="font-semibold tabular-nums"
										>{item.count}</span
									>
								</div>
								<div class="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
									<div
										class="h-full rounded-full bg-primary-500"
										style={`width:${(item.count / maxReason) * 100}%`}
									></div>
								</div>
							</li>{/each}
					</ul>
				{:else}<p class="text-sm text-text-muted">No reason codes recorded.</p>{/if}
			</Card.Content>
		</Card.Root>
	</div>

	<div class="mt-4 grid gap-4 xl:grid-cols-3">
		<Card.Root class="xl:col-span-2">
			<Card.Header
				><Card.Title>Decision volume trend</Card.Title><Card.Description
					>Daily production volume.</Card.Description
				></Card.Header
			>
			<Card.Content>
				{#if trendError}<ErrorNote error={trendError} />{:else if loadingTrend}<Skeleton
						class="h-40 w-full"
					/>{:else if trend?.buckets.length}
					<div class="flex h-40 items-end gap-2" data-testid="trend-chart">
						{#each trend.buckets as bucket (bucket.date)}<div
								class="flex min-w-0 flex-1 flex-col items-center justify-end"
							>
								<div
									class="w-full rounded-t bg-primary-600 transition hover:bg-primary-500"
									style={`height:${Math.max(4, (bucket.total / maxBucket) * 100)}%`}
									title={`${bucket.date}: ${bucket.total}`}
								></div>
								<span class="mt-1 text-[10px] text-text-faint">{bucket.date.slice(5)}</span>
							</div>{/each}
					</div>
				{:else}<p class="text-sm text-text-muted">No decisions in this window.</p>{/if}
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header
				><Card.Title>Review SLA snapshot</Card.Title><Card.Description
					>Current queue and runtime health.</Card.Description
				></Card.Header
			>
			<Card.Content class="space-y-4">
				{#if loadingSummary}<Skeleton class="h-24 w-full" />{:else}
					<div>
						<p class="text-[11px] font-medium uppercase tracking-wide text-text-muted">
							Open review queue
						</p>
						<p class="mt-1 text-3xl font-semibold tabular-nums">
							{summary?.manual_review_queue_size ?? 0}
						</p>
					</div>
					<div class="border-t border-border pt-3">
						<p class="text-[11px] font-medium uppercase tracking-wide text-text-muted">
							API latency P95
						</p>
						<p class="mt-1 text-lg font-semibold tabular-nums">
							{summary?.api_latency_p95_ms == null
								? '—'
								: `${Math.round(summary.api_latency_p95_ms)} ms`}
						</p>
					</div>
				{/if}
			</Card.Content>
		</Card.Root>
	</div>

	<div class="mt-4 grid gap-4 xl:grid-cols-3">
		<Card.Root>
			<Card.Header
				><Card.Title>Score distribution</Card.Title><Card.Description
					>Risk grades in the five most recent decisions.</Card.Description
				></Card.Header
			>
			<Card.Content>
				{#if loadingRecent}<Skeleton class="h-28 w-full" />{:else if gradeCounts.length}<div
						class="space-y-3"
					>
						{#each gradeCounts as [grade, count] (grade)}<div>
								<div class="mb-1 flex justify-between text-xs">
									<span class="font-mono">{grade}</span><span class="font-semibold tabular-nums"
										>{count}</span
									>
								</div>
								<div class="h-1.5 rounded-full bg-surface-sunken">
									<div
										class="h-full rounded-full bg-info"
										style={`width:${(count / maxGrade) * 100}%`}
									></div>
								</div>
							</div>{/each}
					</div>{:else}<p class="text-sm text-text-muted">No score grades available.</p>{/if}
			</Card.Content>
		</Card.Root>
		<div class="xl:col-span-2">
			<div class="mb-2 flex items-center justify-between">
				<h2 class="text-sm font-semibold">Recent decisions</h2>
				<Button variant="ghost" size="sm" href="/decisions"
					>View all <ArrowRight size={14} /></Button
				>
			</div>
			{#if recentError}<ErrorNote error={recentError} />{:else}<DataTable
					columns={recentColumns}
					rows={recentRows}
					loading={loadingRecent}
					rowKey="decision_id"
					onRowClick={(row) => goto(`/decisions/${row.decision_id}`)}
					empty={{ title: 'No recent decisions' }}
				/>{/if}
		</div>
	</div>
{/if}
