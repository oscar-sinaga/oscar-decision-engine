<script lang="ts">
	import { api } from '$lib/api/client';
	import type { DecisionSummary, Meta } from '$lib/api/types';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { formatPercent } from '$lib/format';

	let summary = $state<DecisionSummary | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let productType = $state('');
	let channel = $state('');

	async function load() {
		error = null;
		try {
			summary = await api<DecisionSummary>('/v1/monitoring/decision-summary', {
				query: { product_type: productType || undefined, channel: channel || undefined }
			});
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
		api<Meta>('/v1/meta')
			.then((m) => (meta = m))
			.catch(() => {});
	});
</script>

<h1 class="mb-4 text-xl font-bold text-slate-800">Dashboard</h1>

<div class="mb-4 flex items-end gap-3">
	<label class="text-xs font-semibold text-slate-600">
		Product
		<select class="mt-1 block rounded border-slate-300 text-sm" bind:value={productType}>
			<option value="">All products</option>
			{#each meta?.product_types ?? [] as product (product)}
				<option value={product}>{product}</option>
			{/each}
		</select>
	</label>
	<label class="text-xs font-semibold text-slate-600">
		Channel
		<input
			class="mt-1 block rounded border-slate-300 text-sm"
			placeholder="e.g. BRANCH"
			bind:value={channel}
		/>
	</label>
	<button
		class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
		onclick={load}>Apply</button
	>
</div>

{#if error}
	<ErrorNote {error} />
{:else if summary}
	<div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6" data-testid="kpi-cards">
		<Card title="Applications">
			<span class="text-2xl font-bold text-slate-800">{summary.total_applications}</span>
		</Card>
		<Card title="Approval rate">
			<span class="text-2xl font-bold text-emerald-700">{formatPercent(summary.approval_rate)}</span
			>
		</Card>
		<Card title="Reject rate">
			<span class="text-2xl font-bold text-red-700">{formatPercent(summary.reject_rate)}</span>
		</Card>
		<Card title="Manual review">
			<span class="text-2xl font-bold text-amber-700"
				>{formatPercent(summary.manual_review_rate)}</span
			>
		</Card>
		<Card title="Latency P95">
			<span class="text-2xl font-bold text-slate-800">
				{summary.api_latency_p95_ms === null ? '—' : `${Math.round(summary.api_latency_p95_ms)} ms`}
			</span>
		</Card>
		<Card title="Review queue">
			<span class="text-2xl font-bold text-slate-800">{summary.manual_review_queue_size}</span>
		</Card>
	</div>

	<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
		<Card title="Decision distribution">
			{#if Object.keys(summary.decision_counts).length === 0}
				<p class="text-sm text-slate-500">No decisions in this window.</p>
			{:else}
				<ul class="space-y-2">
					{#each Object.entries(summary.decision_counts) as [decision, count] (decision)}
						<li class="flex items-center justify-between text-sm">
							<span class="text-slate-700">{decision.replaceAll('_', ' ')}</span>
							<span class="font-semibold text-slate-900">{count}</span>
						</li>
					{/each}
				</ul>
			{/if}
		</Card>
		<Card title="Top reason codes">
			{#if summary.top_reason_codes.length === 0}
				<p class="text-sm text-slate-500">No reason codes recorded.</p>
			{:else}
				<ul class="space-y-2">
					{#each summary.top_reason_codes as item (item.code)}
						<li class="flex items-center justify-between text-sm">
							<span class="font-mono text-xs text-slate-700">{item.code}</span>
							<span class="font-semibold text-slate-900">{item.count}</span>
						</li>
					{/each}
				</ul>
			{/if}
		</Card>
	</div>
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
