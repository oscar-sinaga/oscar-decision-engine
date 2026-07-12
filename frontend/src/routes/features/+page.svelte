<script lang="ts">
	import { Check, Plus, Power, PowerOff } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { Feature, RuleCategoryCatalog } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Textarea } from '$lib/components/ui/textarea';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import FilterBar from '$lib/ui/FilterBar.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';

	type FeatureRow = Feature & Record<string, unknown> & { status: string; actions: string };
	let features = $state<Feature[] | null>(null);
	let categories = $state<RuleCategoryCatalog[]>([]);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let sourceFilter = $state('');
	let typeFilter = $state('');
	let categoryFilter = $state('');
	let outputsOnly = $state(false);
	let showCreate = $state(false);
	let loading = $state(true);
	let categoryCode = $state('');
	let categoryLabel = $state('');
	let form = $state({
		path: '',
		label: '',
		description: '',
		data_type: 'NUMBER',
		source: 'PAYLOAD',
		category: 'APPLICANT',
		writable: false
	});
	const canManage = $derived(auth.hasPermission('rule.create'));
	const rows = $derived.by(
		() =>
			(features ?? [])
				.filter((feature) => !typeFilter || feature.data_type === typeFilter)
				.filter((feature) => !categoryFilter || feature.category === categoryFilter)
				.map((feature) => ({
					...feature,
					status: feature.active ? 'ACTIVE' : 'RETIRED',
					actions: ''
				})) as FeatureRow[]
	);
	const featureCategories = $derived(
		[...new Set((features ?? []).map((feature) => feature.category))].sort()
	);

	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			[features, categories] = await Promise.all([
				api<Feature[]>('/v1/features', {
					query: { source: sourceFilter || undefined, writable: outputsOnly || undefined }
				}),
				api<RuleCategoryCatalog[]>('/v1/rule-categories')
			]);
		} catch (err) {
			error = err;
		} finally {
			loading = false;
		}
	}
	$effect(() => {
		load();
	});

	async function createFeature(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		actionError = null;
		try {
			await api('/v1/features', { body: { ...form } });
			showCreate = false;
			form = {
				path: '',
				label: '',
				description: '',
				data_type: 'NUMBER',
				source: 'PAYLOAD',
				category: 'APPLICANT',
				writable: false
			};
			await load();
		} catch (err) {
			actionError = err;
		}
	}
	async function toggleActive(feature: Feature): Promise<void> {
		actionError = null;
		try {
			await api(`/v1/features/${feature.id}`, {
				method: 'PATCH',
				body: { active: !feature.active }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}
	async function toggleWritable(feature: Feature): Promise<void> {
		actionError = null;
		try {
			await api(`/v1/features/${feature.id}`, {
				method: 'PATCH',
				body: { writable: !feature.writable }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}
	async function createCategory(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		actionError = null;
		try {
			await api('/v1/rule-categories', {
				body: { code: categoryCode.trim().toUpperCase(), label: categoryLabel.trim() }
			});
			categoryCode = '';
			categoryLabel = '';
			await load();
		} catch (err) {
			actionError = err;
		}
	}
	async function toggleCategory(category: RuleCategoryCatalog): Promise<void> {
		actionError = null;
		try {
			await api(`/v1/rule-categories/${category.id}`, {
				method: 'PATCH',
				body: { active: !category.active }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}
	function resetFilters(): void {
		sourceFilter = '';
		typeFilter = '';
		categoryFilter = '';
		outputsOnly = false;
		load();
	}
</script>

{#snippet pathCell(row: FeatureRow)}<span class="font-mono text-xs font-medium">{row.path}</span
	>{/snippet}
{#snippet writableCell(row: FeatureRow)}{#if row.writable}<Check
			size={15}
			class="text-success"
			aria-label="Writable"
		/>{:else}<span class="text-text-faint">—</span>{/if}{/snippet}
{#snippet statusCell(row: FeatureRow)}<StatusBadge value={row.status} />{/snippet}
{#snippet updatedCell(row: FeatureRow)}{#if row.created_at}<RelativeTime
			value={row.created_at}
		/>{:else}—{/if}{/snippet}
{#snippet actionsCell(row: FeatureRow)}
	{#if canManage}
		<div class="flex justify-end gap-1">
			<Button
				variant="ghost"
				size="xs"
				disabled={row.source === 'PAYLOAD'}
				onclick={(event) => {
					event.stopPropagation();
					toggleWritable(row);
				}}>{row.writable ? 'Read-only' : 'Writable'}</Button
			>
			<Button
				variant="ghost"
				size="icon-xs"
				onclick={(event) => {
					event.stopPropagation();
					toggleActive(row);
				}}
				aria-label={row.active ? 'Deactivate feature' : 'Activate feature'}
				title={row.active ? 'Deactivate' : 'Activate'}
			>
				{#if row.active}<PowerOff size={13} />{:else}<Power size={13} />{/if}
			</Button>
		</div>
	{/if}
{/snippet}

{#if true}
	{@const columns: Column<FeatureRow>[] = [
		{ key: 'path', header: 'Path', sortable: true, cell: pathCell },
		{ key: 'label', header: 'Label', sortable: true },
		{ key: 'data_type', header: 'Type', sortable: true },
		{ key: 'source', header: 'Source', sortable: true },
		{ key: 'category', header: 'Category', sortable: true },
		{ key: 'writable', header: 'Writable', cell: writableCell },
		{ key: 'status', header: 'Status', cell: statusCell },
		{ key: 'created_at', header: 'Updated', cell: updatedCell },
		{ key: 'actions', header: '', align: 'right', cell: actionsCell }
	]}
	{#snippet actions()}{#if canManage}<Button size="sm" onclick={() => (showCreate = true)}
				><Plus size={15} /> New feature</Button
			>{/if}{/snippet}
	<PageHeader
		title="Feature Catalog"
		description="Governed vocabulary available to rules, tables, and decision flows."
		{actions}
	/>
	<FilterBar onReset={resetFilters}>
		<label class="min-w-40 text-xs font-medium text-text-muted"
			>Source<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={sourceFilter}
				onchange={load}
				><option value="">All</option><option>PAYLOAD</option><option>DERIVED</option><option
					>SCORE</option
				><option>RULE_OUTPUT</option></select
			></label
		>
		<label class="min-w-36 text-xs font-medium text-text-muted"
			>Type<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={typeFilter}
				><option value="">All</option><option>NUMBER</option><option>STRING</option><option
					>BOOLEAN</option
				><option>DATE</option></select
			></label
		>
		<label class="min-w-44 text-xs font-medium text-text-muted"
			>Category<select
				class="mt-1 block h-9 w-full rounded-control border-border text-sm"
				bind:value={categoryFilter}
				><option value="">All</option>{#each featureCategories as category (category)}<option
						>{category}</option
					>{/each}</select
			></label
		>
		<label class="flex items-center gap-2 self-end pb-2 text-xs font-medium text-text-muted"
			><Checkbox bind:checked={outputsOnly} onchange={load} /> Outputs only</label
		>
	</FilterBar>
	{#if actionError}<div class="mb-4"><ErrorNote error={actionError} /></div>{/if}
	{#if error}<ErrorNote {error} />{:else}<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="id"
			testId="features-table"
			empty={{ title: 'No features', hint: 'No catalog entries match the selected filters.' }}
		/>{/if}

	<Card.Root class="mt-6">
		<Card.Header
			><Card.Title>Rule categories</Card.Title><Card.Description
				>Managed categories shown in the rule authoring experience.</Card.Description
			></Card.Header
		>
		<Card.Content>
			{#if canManage}
				<form class="mb-4 flex flex-wrap items-end gap-2" onsubmit={createCategory}>
					<div class="space-y-1.5">
						<Label for="category-code">Code</Label><Input
							id="category-code"
							bind:value={categoryCode}
							required
							minlength={2}
						/>
					</div>
					<div class="space-y-1.5">
						<Label for="category-label">Label</Label><Input
							id="category-label"
							bind:value={categoryLabel}
							required
						/>
					</div>
					<Button size="sm" type="submit">Add category</Button>
				</form>
			{/if}
			<div class="flex flex-wrap gap-2" data-testid="rule-categories">
				{#each categories as category (category.id)}
					<div
						class="flex items-center gap-2 rounded-control border border-border bg-surface-muted px-2.5 py-1.5 text-xs"
					>
						<span class:line-through={!category.active}
							><strong class="font-mono">{category.code}</strong> · {category.label}</span
						>
						{#if canManage}<Button
								variant="ghost"
								size="xs"
								onclick={() => toggleCategory(category)}
								>{category.active ? 'Deactivate' : 'Activate'}</Button
							>{/if}
					</div>
				{/each}
			</div>
		</Card.Content>
	</Card.Root>

	<Sheet.Root bind:open={showCreate}>
		<Sheet.Content class="overflow-y-auto sm:max-w-lg">
			<Sheet.Header
				><Sheet.Title>New feature</Sheet.Title><Sheet.Description
					>Add a governed input, derived value, score, or writable rule output.</Sheet.Description
				></Sheet.Header
			>
			<form class="space-y-4 px-4 pb-6" onsubmit={createFeature}>
				<div class="space-y-1.5">
					<Label for="feature-path">Path (dotted)</Label><Input
						id="feature-path"
						class="font-mono"
						placeholder="applicant.custom_score"
						bind:value={form.path}
						required
					/>
				</div>
				<div class="space-y-1.5">
					<Label for="feature-label">Label</Label><Input
						id="feature-label"
						bind:value={form.label}
						required
					/>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div class="space-y-1.5">
						<Label for="feature-type">Data type</Label><select
							id="feature-type"
							class="block h-9 w-full rounded-control border-border text-sm"
							bind:value={form.data_type}
							><option>NUMBER</option><option>STRING</option><option>BOOLEAN</option><option
								>DATE</option
							></select
						>
					</div>
					<div class="space-y-1.5">
						<Label for="feature-source">Source</Label><select
							id="feature-source"
							class="block h-9 w-full rounded-control border-border text-sm"
							bind:value={form.source}
							><option>PAYLOAD</option><option>DERIVED</option><option>SCORE</option><option
								>RULE_OUTPUT</option
							></select
						>
					</div>
				</div>
				<div class="space-y-1.5">
					<Label for="feature-category">Category</Label><Input
						id="feature-category"
						bind:value={form.category}
					/>
				</div>
				<div class="space-y-1.5">
					<Label for="feature-description">Description</Label><Textarea
						id="feature-description"
						rows={3}
						bind:value={form.description}
					/>
				</div>
				<label class="flex items-center gap-2 text-sm"
					><Checkbox bind:checked={form.writable} /> Writable output</label
				>
				{#if actionError}<ErrorNote error={actionError} />{/if}
				<div class="flex justify-end gap-2">
					<Button variant="outline" onclick={() => (showCreate = false)}>Cancel</Button><Button
						type="submit">Create feature</Button
					>
				</div>
			</form>
		</Sheet.Content>
	</Sheet.Root>
{/if}
