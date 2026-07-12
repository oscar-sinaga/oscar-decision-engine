<script lang="ts">
	import { goto } from '$app/navigation';
	import { AlarmClock, Search } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { ManualReviewCase, Meta, Page } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import FilterBar from '$lib/ui/FilterBar.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	type CaseRow = ManualReviewCase & Record<string, unknown>;
	let result = $state<Page<ManualReviewCase> | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let filters = $state({ status: '', priority: '' });
	let page = $state(1);
	let loading = $state(true);
	const rows = $derived((result?.items ?? []) as CaseRow[]);
	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			result = await api<Page<ManualReviewCase>>('/v1/manual-review/cases', {
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
	function apply(): void {
		page = 1;
		load();
	}
</script>

{#snippet caseCell(row: CaseRow)}<span class="font-mono text-xs font-medium">{row.case_id}</span
	>{/snippet}
{#snippet priorityCell(row: CaseRow)}<StatusBadge
		value={row.priority === 'CRITICAL' ? 'ESCALATED' : row.priority}
	/>{/snippet}
{#snippet statusCell(row: CaseRow)}<StatusBadge value={row.status} />{/snippet}
{#snippet slaCell(row: CaseRow)}
	{#if row.sla_breached}<span class="inline-flex items-center gap-1 font-semibold text-danger"
			><AlarmClock size={14} /> breached</span
		>{:else if row.sla_due_at}<RelativeTime value={row.sla_due_at} />{:else}—{/if}
{/snippet}
{#if true}
	{@const columns: Column<CaseRow>[] = [
		{ key: 'case_id', header: 'Case', sortable: true, cell: caseCell },
		{ key: 'application_id', header: 'Application', sortable: true },
		{ key: 'priority', header: 'Priority', sortable: true, cell: priorityCell },
		{ key: 'status', header: 'Status', sortable: true, cell: statusCell },
		{ key: 'sla_due_at', header: 'SLA deadline', sortable: true, cell: slaCell },
		{ key: 'assigned_to', header: 'Assigned to', sortable: true }
	]}
	<PageHeader title="Manual Review" description="Triage cases by priority, SLA, and assignment." />
	<FilterBar
		onReset={() => {
			filters = { status: '', priority: '' };
			apply();
		}}
	>
		<label class="min-w-44 text-xs font-medium text-text-muted"
			>Status<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={filters.status}
				><option value="">All</option>{#each meta?.case_statuses ?? [] as status (status)}<option
						value={status}>{status}</option
					>{/each}</select
			></label
		>
		<label class="min-w-44 text-xs font-medium text-text-muted"
			>Priority<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={filters.priority}
				><option value="">All</option
				>{#each meta?.case_priorities ?? [] as priority (priority)}<option value={priority}
						>{priority}</option
					>{/each}</select
			></label
		>
		<Button size="sm" onclick={apply}><Search size={15} /> Filter</Button>
	</FilterBar>
	{#if error}<ErrorNote {error} />{:else}<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="case_id"
			testId="case-table"
			onRowClick={(row) => goto(`/manual-review/${row.case_id}`)}
			empty={{ title: 'Queue is empty', hint: 'There are no review cases matching these filters.' }}
		/>{/if}
	{#if result && result.total > 0}<div class="mt-3">
			<Pagination
				{page}
				pageSize={result.page_size}
				total={result.total}
				onchange={(next) => {
					page = next;
					load();
				}}
			/>
		</div>{/if}
{/if}
