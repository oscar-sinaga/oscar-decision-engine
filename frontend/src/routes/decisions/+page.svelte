<script lang="ts">
	import { api } from '$lib/api/client';
	import type { DecisionHistoryItem, Meta, Page } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import { formatCurrency, formatDateTime } from '$lib/format';

	let result = $state<Page<DecisionHistoryItem> | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let filters = $state({ application_id: '', decision: '', product_type: '', channel: '' });
	let page = $state(1);

	async function load() {
		error = null;
		try {
			result = await api<Page<DecisionHistoryItem>>('/v1/decisions', {
				query: { ...filters, page, page_size: 25 }
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

	function applyFilters() {
		page = 1;
		load();
	}
</script>

<h1 class="mb-4 text-xl font-bold text-slate-800">Decision History</h1>

<div class="mb-4 flex flex-wrap items-end gap-3 text-xs font-semibold text-slate-600">
	<label>
		Application ID
		<input
			class="mt-1 block rounded border-slate-300 text-sm"
			bind:value={filters.application_id}
		/>
	</label>
	<label>
		Decision
		<select class="mt-1 block rounded border-slate-300 text-sm" bind:value={filters.decision}>
			<option value="">All</option>
			{#each meta?.decisions ?? [] as decision (decision)}
				<option value={decision}>{decision}</option>
			{/each}
		</select>
	</label>
	<label>
		Product
		<select class="mt-1 block rounded border-slate-300 text-sm" bind:value={filters.product_type}>
			<option value="">All</option>
			{#each meta?.product_types ?? [] as product (product)}
				<option value={product}>{product}</option>
			{/each}
		</select>
	</label>
	<label>
		Channel
		<input class="mt-1 block rounded border-slate-300 text-sm" bind:value={filters.channel} />
	</label>
	<button
		class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
		onclick={applyFilters}>Search</button
	>
</div>

{#if error}
	<ErrorNote {error} />
{:else if result}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="decision-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Decision ID</th>
					<th class="px-3 py-2">Application</th>
					<th class="px-3 py-2">Product</th>
					<th class="px-3 py-2">Channel</th>
					<th class="px-3 py-2">Decision</th>
					<th class="px-3 py-2">Grade</th>
					<th class="px-3 py-2">Score</th>
					<th class="px-3 py-2">Approved limit</th>
					<th class="px-3 py-2">Reasons</th>
					<th class="px-3 py-2">Created</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each result.items as item (item.decision_id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2">
							<a
								class="font-mono text-xs text-blue-700 underline"
								href="/decisions/{item.decision_id}"
							>
								{item.decision_id}
							</a>
						</td>
						<td class="px-3 py-2 font-mono text-xs">{item.application_id}</td>
						<td class="px-3 py-2 text-xs">{item.product_type}</td>
						<td class="px-3 py-2 text-xs">{item.channel}</td>
						<td class="px-3 py-2"><Badge value={item.decision} kind="decision" /></td>
						<td class="px-3 py-2">{item.risk_grade ?? '—'}</td>
						<td class="px-3 py-2">{item.score ?? '—'}</td>
						<td class="px-3 py-2">{formatCurrency(item.approved_limit)}</td>
						<td class="px-3 py-2 font-mono text-[11px]">{item.reason_codes.join(', ') || '—'}</td>
						<td class="px-3 py-2 text-xs whitespace-nowrap">{formatDateTime(item.created_at)}</td>
					</tr>
				{:else}
					<tr
						><td class="px-3 py-6 text-center text-slate-400" colspan="10">No decisions found</td
						></tr
					>
				{/each}
			</tbody>
		</table>
	</div>
	<div class="mt-3">
		<Pagination
			{page}
			pageSize={result.page_size}
			total={result.total}
			onchange={(next) => {
				page = next;
				load();
			}}
		/>
	</div>
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
