<script lang="ts">
	import { appPath } from '$lib/app-path';

	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import type { Strategy } from '$lib/api/types';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	type StrategyRow = Strategy & Record<string, unknown> & { product_segment: string };
	let strategies = $state<Strategy[] | null>(null);
	let error = $state<unknown>(null);
	let loading = $state(true);
	const rows = $derived(
		(strategies ?? []).map((strategy) => ({
			...strategy,
			product_segment: `${strategy.product_type} / ${strategy.segment}`
		})) as StrategyRow[]
	);

	$effect(() => {
		loading = true;
		api<Strategy[]>('/v1/strategies')
			.then((value) => (strategies = value))
			.catch((err) => (error = err))
			.finally(() => (loading = false));
	});
</script>

{#snippet codeCell(row: StrategyRow)}<span class="font-mono text-xs font-medium"
		>{row.strategy_code}</span
	>{/snippet}
{#snippet statusCell(row: StrategyRow)}
	{#if row.latest_version}<div class="flex items-center gap-2">
			<span class="font-mono">v{row.latest_version}</span><StatusBadge
				value={row.latest_status ?? 'UNKNOWN'}
			/>
		</div>{:else}—{/if}
{/snippet}
{#if true}
	{@const columns: Column<StrategyRow>[] = [
	{ key: 'strategy_code', header: 'Code', sortable: true, cell: codeCell },
	{ key: 'name', header: 'Name', sortable: true },
	{ key: 'product_segment', header: 'Product / Segment', sortable: true },
	{ key: 'active_version', header: 'Active vN', align: 'right' },
	{ key: 'latest_version', header: 'Latest status', cell: statusCell }
]}

	<PageHeader
		title="Strategies"
		description="Compose validation, rules, scorecards, and tables into governed decision flows."
	/>
	{#if error}
		<ErrorNote {error} />
	{:else}
		<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="id"
			testId="strategies-table"
			onRowClick={(row) => goto(appPath(`/strategies/${row.id}`))}
			empty={{
				title: 'No strategies',
				hint: 'Strategies appear here after they are created through the existing API workflow.'
			}}
		/>
	{/if}
{/if}
