<script lang="ts">
	import { goto } from '$app/navigation';
	import { Search } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { DecisionHistoryItem, Meta, Page } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import FilterBar from '$lib/ui/FilterBar.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	type DecisionRow = DecisionHistoryItem & Record<string, unknown>;

	let result = $state<Page<DecisionHistoryItem> | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let filters = $state({ application_id: '', decision: '', product_type: '', channel: '' });
	let page = $state(1);
	let loading = $state(true);

	const rows = $derived((result?.items ?? []) as DecisionRow[]);

	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			result = await api<Page<DecisionHistoryItem>>('/v1/decisions', {
				query: { ...filters, page, page_size: 25 }
			});
		} catch (err) {
			error = err;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
		api<Meta>('/v1/meta')
			.then((m) => (meta = m))
			.catch(() => {});
	});

	function applyFilters(): void {
		page = 1;
		load();
	}

	function resetFilters(): void {
		filters = { application_id: '', decision: '', product_type: '', channel: '' };
		applyFilters();
	}
</script>

{#snippet applicationCell(row: DecisionRow)}
	<div>
		<div class="font-mono text-xs font-medium text-text">{row.application_id}</div>
		<div class="font-mono text-[10px] text-text-faint">{row.decision_id}</div>
	</div>
{/snippet}

{#snippet decisionCell(row: DecisionRow)}<StatusBadge value={row.decision} />{/snippet}

{#snippet reasonsCell(row: DecisionRow)}
	{#if row.reason_codes.length}
		<span class="font-mono text-[11px]" title={row.reason_codes.join(', ')}>
			{row.reason_codes[0]}{row.reason_codes.length > 1 ? ` +${row.reason_codes.length - 1}` : ''}
		</span>
	{:else}—{/if}
{/snippet}

{#snippet strategyCell(row: DecisionRow)}
	<span class="font-mono text-[11px]">{row.strategy_version_id}</span>
{/snippet}

{#snippet createdCell(row: DecisionRow)}<RelativeTime value={row.created_at} />{/snippet}

{#if true}
	{@const columns: Column<DecisionRow>[] = [
	{ key: 'application_id', header: 'Application', sortable: true, cell: applicationCell },
	{ key: 'decision', header: 'Decision', sortable: true, cell: decisionCell },
	{ key: 'reason_codes', header: 'Reason codes', cell: reasonsCell },
	{ key: 'strategy_version_id', header: 'Strategy version', cell: strategyCell },
	{ key: 'product_type', header: 'Product', sortable: true },
	{ key: 'channel', header: 'Channel', sortable: true },
	{ key: 'created_at', header: 'Created', sortable: true, cell: createdCell }
]}

	<PageHeader
		title="Decisions"
		description="Search production decisions and inspect the exact strategy trace."
	/>

	<FilterBar onReset={resetFilters}>
		<label class="min-w-48 text-xs font-medium text-text-muted">
			Application ID
			<Input class="mt-1" bind:value={filters.application_id} placeholder="APP-…" />
		</label>
		<label class="min-w-40 text-xs font-medium text-text-muted">
			Decision
			<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={filters.decision}
			>
				<option value="">All</option>
				{#each meta?.decisions ?? [] as decision (decision)}<option value={decision}
						>{decision}</option
					>{/each}
			</select>
		</label>
		<label class="min-w-44 text-xs font-medium text-text-muted">
			Product
			<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={filters.product_type}
			>
				<option value="">All</option>
				{#each meta?.product_types ?? [] as product (product)}<option value={product}
						>{product}</option
					>{/each}
			</select>
		</label>
		<label class="min-w-40 text-xs font-medium text-text-muted">
			Channel
			<Input class="mt-1" bind:value={filters.channel} />
		</label>
		<Button size="sm" onclick={applyFilters}><Search size={15} /> Search</Button>
	</FilterBar>

	{#if error}
		<ErrorNote {error} />
	{:else}
		<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="decision_id"
			testId="decision-table"
			onRowClick={(row) => goto(`/decisions/${row.decision_id}`)}
			empty={{
				title: 'No decisions match these filters',
				hint: 'Reset or broaden the search criteria.'
			}}
		/>
		{#if result && result.total > 0}
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
		{/if}
	{/if}
{/if}
