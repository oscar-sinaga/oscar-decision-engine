<script lang="ts">
	import { api } from '$lib/api/client';
	import type { ManualReviewCase, Meta, Page } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import { formatDateTime } from '$lib/format';

	let result = $state<Page<ManualReviewCase> | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let filters = $state({ status: '', priority: '' });
	let page = $state(1);

	async function load() {
		error = null;
		try {
			result = await api<Page<ManualReviewCase>>('/v1/manual-review/cases', {
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
</script>

<h1 class="mb-4 text-xl font-bold text-slate-800">Manual Review Queue</h1>

<div class="mb-4 flex items-end gap-3 text-xs font-semibold text-slate-600">
	<label>
		Status
		<select class="mt-1 block rounded border-slate-300 text-sm" bind:value={filters.status}>
			<option value="">All</option>
			{#each meta?.case_statuses ?? [] as status (status)}
				<option value={status}>{status}</option>
			{/each}
		</select>
	</label>
	<label>
		Priority
		<select class="mt-1 block rounded border-slate-300 text-sm" bind:value={filters.priority}>
			<option value="">All</option>
			{#each meta?.case_priorities ?? [] as priority (priority)}
				<option value={priority}>{priority}</option>
			{/each}
		</select>
	</label>
	<button
		class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
		onclick={() => {
			page = 1;
			load();
		}}>Filter</button
	>
</div>

{#if error}
	<ErrorNote {error} />
{:else if result}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="case-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Case ID</th>
					<th class="px-3 py-2">Application</th>
					<th class="px-3 py-2">Product</th>
					<th class="px-3 py-2">System decision</th>
					<th class="px-3 py-2">Reasons</th>
					<th class="px-3 py-2">Priority</th>
					<th class="px-3 py-2">SLA</th>
					<th class="px-3 py-2">Assigned to</th>
					<th class="px-3 py-2">Status</th>
					<th class="px-3 py-2">Created</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each result.items as item (item.case_id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2">
							<a
								class="font-mono text-xs text-blue-700 underline"
								href="/manual-review/{item.case_id}"
							>
								{item.case_id}
							</a>
						</td>
						<td class="px-3 py-2 font-mono text-xs">{item.application_id}</td>
						<td class="px-3 py-2 text-xs">{item.product_type}</td>
						<td class="px-3 py-2"><Badge value={item.system_decision} kind="decision" /></td>
						<td class="px-3 py-2 font-mono text-[11px]">{item.system_reason_codes.join(', ')}</td>
						<td class="px-3 py-2 text-xs">{item.priority}</td>
						<td class="px-3 py-2 text-xs">
							{#if item.sla_breached}
								<span class="font-semibold text-red-700">breached</span>
							{:else if item.sla_due_at}
								<span class="text-slate-500">{formatDateTime(item.sla_due_at)}</span>
							{:else}—{/if}
						</td>
						<td class="px-3 py-2 text-xs">{item.assigned_to ?? '—'}</td>
						<td class="px-3 py-2"><Badge value={item.status} /></td>
						<td class="px-3 py-2 text-xs whitespace-nowrap">{formatDateTime(item.created_at)}</td>
					</tr>
				{:else}
					<tr><td class="px-3 py-6 text-center text-slate-400" colspan="10">Queue is empty</td></tr>
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
