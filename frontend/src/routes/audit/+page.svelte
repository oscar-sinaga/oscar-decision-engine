<script lang="ts">
	import { Copy, Search } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { AuditLogItem, Page } from '$lib/api/types';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as Sheet from '$lib/components/ui/sheet';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import DiffView from '$lib/ui/DiffView.svelte';
	import { toast } from 'svelte-sonner';
	import Pagination from '$lib/components/Pagination.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import FilterBar from '$lib/ui/FilterBar.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';

	type AuditRow = AuditLogItem & Record<string, unknown> & { entity: string };
	let result = $state<Page<AuditLogItem> | null>(null);
	let error = $state<unknown>(null);
	let filters = $state({ event_type: '', entity_type: '', entity_id: '', actor: '' });
	let page = $state(1);
	let loading = $state(true);
	let selected = $state<AuditLogItem | null>(null);
	const rows = $derived(
		(result?.items ?? []).map((item) => ({
			...item,
			entity: `${item.entity_type} · ${item.entity_id}`
		})) as AuditRow[]
	);
	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			result = await api<Page<AuditLogItem>>('/v1/audit-logs', {
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
	});
	function apply(): void {
		page = 1;
		load();
	}
	function reset(): void {
		filters = { event_type: '', entity_type: '', entity_id: '', actor: '' };
		apply();
	}
	async function copyCorrelation(): Promise<void> {
		if (selected?.correlation_id && navigator.clipboard) {
			await navigator.clipboard.writeText(selected.correlation_id);
			toast.success('Correlation ID copied');
		}
	}
</script>

{#snippet timeCell(row: AuditRow)}<RelativeTime value={row.created_at} />{/snippet}
{#snippet eventCell(row: AuditRow)}<span class="font-mono text-[11px] font-medium"
		>{row.event_type}</span
	>{/snippet}
{#snippet entityCell(row: AuditRow)}<div>
		<span class="text-xs">{row.entity_type}</span><span
			class="block max-w-52 truncate font-mono text-[10px] text-text-muted">{row.entity_id}</span
		>
	</div>{/snippet}
{#snippet actorCell(row: AuditRow)}<div>
		{row.actor_label}<span class="block text-[10px] text-text-muted">{row.actor_type}</span>
	</div>{/snippet}
{#snippet reasonCell(row: AuditRow)}<span class="block max-w-64 truncate" title={row.reason ?? ''}
		>{row.reason ?? '—'}</span
	>{/snippet}
{#if true}
	{@const columns: Column<AuditRow>[] = [
		{ key: 'created_at', header: 'Time', sortable: true, cell: timeCell },
		{ key: 'event_type', header: 'Event', sortable: true, cell: eventCell },
		{ key: 'entity', header: 'Entity', sortable: true, cell: entityCell },
		{ key: 'actor_label', header: 'Actor', sortable: true, cell: actorCell },
		{ key: 'reason', header: 'Reason', cell: reasonCell }
	]}
	<PageHeader
		title="Audit Log"
		description="Append-only governance events, configuration changes, and approvals."
	/>
	<FilterBar onReset={reset}>
		<label class="min-w-52 text-xs font-medium text-text-muted"
			>Event type<Input
				class="mt-1 font-mono"
				placeholder="RULE_VERSION_ACTIVATED"
				bind:value={filters.event_type}
			/></label
		>
		<label class="min-w-40 text-xs font-medium text-text-muted"
			>Entity type<Input class="mt-1 font-mono" bind:value={filters.entity_type} /></label
		>
		<label class="min-w-52 text-xs font-medium text-text-muted"
			>Entity ID<Input class="mt-1 font-mono" bind:value={filters.entity_id} /></label
		>
		<label class="min-w-40 text-xs font-medium text-text-muted"
			>Actor<Input class="mt-1" bind:value={filters.actor} /></label
		>
		<Button size="sm" onclick={apply}><Search size={15} /> Search</Button>
	</FilterBar>
	{#if error}<ErrorNote {error} />{:else}<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="id"
			testId="audit-table"
			onRowClick={(row) => (selected = row)}
			empty={{ title: 'No audit events', hint: 'No governance events match these filters.' }}
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
	<Sheet.Root
		open={selected !== null}
		onOpenChange={(open) => {
			if (!open) selected = null;
		}}
	>
		{#if selected}<Sheet.Content class="overflow-y-auto sm:max-w-2xl"
				><Sheet.Header
					><Sheet.Title>{selected.event_type}</Sheet.Title><Sheet.Description
						>{selected.entity_type} · {selected.entity_id}</Sheet.Description
					></Sheet.Header
				>
				<div class="space-y-4 px-4 pb-6">
					<div class="rounded-card border border-border bg-surface-muted p-3 text-xs">
						<div class="flex items-center justify-between gap-2">
							<span class="font-mono">{selected.correlation_id ?? 'No correlation id'}</span
							>{#if selected.correlation_id}<Button
									variant="ghost"
									size="icon-xs"
									onclick={copyCorrelation}
									aria-label="Copy correlation id"><Copy size={13} /></Button
								>{/if}
						</div>
						<p class="mt-2 text-text-muted">{selected.reason ?? 'No reason recorded.'}</p>
					</div>
					<div>
						<h3 class="mb-2 text-xs font-semibold text-text-muted uppercase">Field changes</h3>
						<DiffView before={selected.before_value} after={selected.after_value} />
					</div>
					<div>
						<h3 class="mb-1 text-xs font-semibold text-text-muted uppercase">Metadata</h3>
						<JsonBlock value={selected.metadata} maxHeight="14rem" />
					</div>
				</div></Sheet.Content
			>{/if}
	</Sheet.Root>
{/if}
