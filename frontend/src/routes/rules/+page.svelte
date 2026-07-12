<script lang="ts">
	import { goto } from '$app/navigation';
	import { Plus, Search } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { Meta, Rule } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import FilterBar from '$lib/ui/FilterBar.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	type RuleRow = Rule & Record<string, unknown>;
	let rules = $state<Rule[] | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let category = $state('');
	let search = $state('');
	let loading = $state(true);

	const rows = $derived.by(() => {
		const query = search.trim().toLowerCase();
		return (rules ?? []).filter(
			(rule) => !query || `${rule.rule_code} ${rule.name}`.toLowerCase().includes(query)
		) as RuleRow[];
	});

	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			rules = await api<Rule[]>('/v1/rules', { query: { category: category || undefined } });
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
</script>

{#snippet codeCell(row: RuleRow)}<span class="font-mono text-xs font-medium">{row.rule_code}</span
	>{/snippet}
{#snippet versionCell(row: RuleRow)}
	<div class="flex items-center gap-2">
		<span class="font-mono">v{row.latest_version}</span><StatusBadge value={row.latest_status} />
	</div>
{/snippet}

{#if true}
	{@const columns: Column<RuleRow>[] = [
	{ key: 'rule_code', header: 'Code', sortable: true, cell: codeCell },
	{ key: 'name', header: 'Name', sortable: true },
	{ key: 'category', header: 'Category', sortable: true },
	{ key: 'owner_team', header: 'Owner' },
	{ key: 'active_version', header: 'Active version', align: 'right' },
	{ key: 'latest_version', header: 'Latest', cell: versionCell }
]}

	{#snippet actions()}
		{#if auth.hasPermission('rule.create')}
			<Button href="/rules/new" size="sm"><Plus size={15} /> New rule</Button>
		{/if}
	{/snippet}

	<PageHeader
		title="Rules"
		description="Author reusable policy, classification, statement, and expression rules."
		{actions}
	/>

	<FilterBar
		onReset={() => {
			category = '';
			search = '';
			load();
		}}
	>
		<label class="min-w-56 text-xs font-medium text-text-muted">
			Search
			<div class="relative mt-1">
				<Search class="absolute top-2.5 left-2.5 text-text-faint" size={14} /><Input
					class="pl-8"
					bind:value={search}
					placeholder="Code or name"
				/>
			</div>
		</label>
		<label class="min-w-44 text-xs font-medium text-text-muted">
			Category
			<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={category}
				onchange={load}
			>
				<option value="">All</option>
				{#each meta?.rule_categories ?? [] as item (item.code)}<option value={item.code}
						>{item.label}</option
					>{/each}
			</select>
		</label>
	</FilterBar>

	{#if error}
		<ErrorNote {error} />
	{:else}
		<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="id"
			testId="rules-table"
			onRowClick={(row) => goto(`/rules/${row.id}`)}
			empty={{
				title: 'No rules found',
				hint: 'Adjust the filters or create a new governed rule.',
				actionLabel: auth.hasPermission('rule.create') ? 'New rule' : undefined,
				onAction: auth.hasPermission('rule.create') ? () => goto('/rules/new') : undefined
			}}
		/>
	{/if}
{/if}
