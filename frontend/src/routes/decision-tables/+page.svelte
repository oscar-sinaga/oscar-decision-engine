<script lang="ts">
	import { appPath } from '$lib/app-path';

	import { goto } from '$app/navigation';
	import { Plus } from '@lucide/svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { ConfigEntity } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Textarea } from '$lib/components/ui/textarea';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import { toast } from 'svelte-sonner';

	type TableRow = ConfigEntity &
		Record<string, unknown> & { hit_policy: string; row_count: number };
	let tables = $state<ConfigEntity[] | null>(null);
	let error = $state<unknown>(null);
	let creating = $state(false);
	let submitting = $state(false);
	let loading = $state(true);
	let code = $state('');
	let name = $state('');
	let description = $state('');

	const rows = $derived(
		(tables ?? []).map((table) => ({
			...table,
			hit_policy: String(table.versions.at(-1)?.config.hit_policy ?? 'FIRST_MATCH'),
			row_count: Array.isArray(table.versions.at(-1)?.config.rows)
				? (table.versions.at(-1)?.config.rows as unknown[]).length
				: 0
		})) as TableRow[]
	);

	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			tables = await api<ConfigEntity[]>('/v1/decision-tables');
		} catch (err) {
			error = err;
		} finally {
			loading = false;
		}
	}

	async function createTable(): Promise<void> {
		submitting = true;
		error = null;
		try {
			const created = await api<ConfigEntity>('/v1/decision-tables', {
				body: {
					code: code.trim().toUpperCase(),
					name: name.trim(),
					description: description.trim(),
					config: {
						hit_policy: 'FIRST_MATCH',
						rows: [{ priority: 0, conditions: [], output: { decision: 'MANUAL_REVIEW' } }],
						no_match_decision: 'MANUAL_REVIEW'
					},
					version_note: 'Initial grid draft'
				}
			});
			toast.success('Decision table created');
			goto(appPath(`/decision-tables/${created.id}`));
		} catch (err) {
			error = err;
			toast.error(err instanceof ApiError ? err.message : 'Could not create decision table');
		} finally {
			submitting = false;
		}
	}

	$effect(() => {
		load();
	});
</script>

{#snippet codeCell(row: TableRow)}<span class="font-mono text-xs font-medium">{row.code}</span
	>{/snippet}
{#snippet statusCell(row: TableRow)}<div class="flex items-center gap-2">
		<span class="font-mono">v{row.latest_version}</span><StatusBadge value={row.latest_status} />
	</div>{/snippet}
{#if true}
	{@const columns: Column<TableRow>[] = [
	{ key: 'code', header: 'Code', sortable: true, cell: codeCell },
	{ key: 'name', header: 'Name', sortable: true },
	{ key: 'hit_policy', header: 'Hit policy' },
	{ key: 'active_version', header: 'Active version', align: 'right' },
	{ key: 'latest_version', header: 'Latest', cell: statusCell },
	{ key: 'row_count', header: 'Rows', align: 'right' }
]}

	{#snippet actions()}
		{#if auth.hasPermission('rule.create')}
			<Button size="sm" onclick={() => (creating = !creating)}><Plus size={15} /> New table</Button>
		{/if}
	{/snippet}
	<PageHeader
		title="Decision Tables"
		description="Author typed policy matrices without editing JSON."
		{actions}
	/>

	{#if error}<div class="mb-4"><ErrorNote {error} /></div>{/if}

	{#if creating}
		<Card.Root class="mb-4">
			<Card.Header
				><Card.Title>Create decision table</Card.Title><Card.Description
					>Start with a governed FIRST_MATCH draft.</Card.Description
				></Card.Header
			>
			<Card.Content>
				<form
					class="grid gap-3 md:grid-cols-2"
					onsubmit={(event) => {
						event.preventDefault();
						createTable();
					}}
				>
					<div class="space-y-1.5">
						<Label for="table-code">Code</Label><Input
							id="table-code"
							bind:value={code}
							required
							minlength={3}
						/>
					</div>
					<div class="space-y-1.5">
						<Label for="table-name">Name</Label><Input id="table-name" bind:value={name} required />
					</div>
					<div class="space-y-1.5 md:col-span-2">
						<Label for="table-description">Description</Label><Textarea
							id="table-description"
							rows={2}
							bind:value={description}
						/>
					</div>
					<div class="flex gap-2 md:col-span-2">
						<Button type="submit" disabled={submitting}
							>{submitting ? 'Creating…' : 'Create and open grid'}</Button
						><Button variant="outline" onclick={() => (creating = false)}>Cancel</Button>
					</div>
				</form>
			</Card.Content>
		</Card.Root>
	{/if}

	<DataTable
		{columns}
		{rows}
		{loading}
		rowKey="id"
		testId="decision-tables-table"
		onRowClick={(row) => goto(appPath(`/decision-tables/${row.id}`))}
		empty={{
			title: 'No decision tables',
			hint: 'Create a table to translate rule outputs into final decisions.',
			actionLabel: auth.hasPermission('rule.create') ? 'New table' : undefined,
			onAction: auth.hasPermission('rule.create') ? () => (creating = true) : undefined
		}}
	/>
{/if}
