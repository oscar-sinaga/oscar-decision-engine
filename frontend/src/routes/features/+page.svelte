<script lang="ts">
	import { api } from '$lib/api/client';
	import type { Feature } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';

	let features = $state<Feature[] | null>(null);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let sourceFilter = $state('');
	let showCreate = $state(false);

	let form = $state({
		path: '',
		label: '',
		description: '',
		data_type: 'NUMBER',
		source: 'PAYLOAD',
		category: 'APPLICANT'
	});

	async function load() {
		error = null;
		try {
			features = await api<Feature[]>('/v1/features', {
				query: { source: sourceFilter || undefined }
			});
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
	});

	async function createFeature(event: SubmitEvent) {
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
				category: 'APPLICANT'
			};
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	async function toggleActive(feature: Feature) {
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

	const canManage = $derived(auth.hasPermission('rule.create'));
</script>

<div class="mb-4 flex items-center justify-between">
	<div>
		<h1 class="text-xl font-bold text-slate-800">Feature Catalog</h1>
		<p class="text-sm text-slate-500">
			Governed data dictionary — the vocabulary rules and strategies may reference.
		</p>
	</div>
	{#if canManage}
		<button
			class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
			onclick={() => (showCreate = !showCreate)}
		>
			{showCreate ? 'Cancel' : 'New feature'}
		</button>
	{/if}
</div>

{#if showCreate}
	<div class="mb-4">
		<Card title="New feature">
			<form
				class="grid grid-cols-2 gap-3 text-xs font-semibold text-slate-600"
				onsubmit={createFeature}
			>
				<label
					>Path (dotted)
					<input
						class="mt-1 w-full rounded border-slate-300 font-mono text-sm"
						placeholder="applicant.custom_score"
						bind:value={form.path}
						required
					/></label
				>
				<label
					>Label
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.label}
						required
					/></label
				>
				<label
					>Data type
					<select class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={form.data_type}>
						<option>NUMBER</option><option>STRING</option><option>BOOLEAN</option><option
							>DATE</option
						>
					</select></label
				>
				<label
					>Source
					<select class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={form.source}>
						<option>PAYLOAD</option><option>DERIVED</option><option>SCORE</option>
					</select></label
				>
				<label
					>Category
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.category}
					/></label
				>
				<label class="col-span-2"
					>Description
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.description}
					/></label
				>
				<div class="col-span-2">
					<button
						class="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
						type="submit">Create feature</button
					>
				</div>
			</form>
			{#if actionError}
				<div class="mt-3"><ErrorNote error={actionError} /></div>
			{/if}
		</Card>
	</div>
{/if}

<div class="mb-4 flex items-end gap-3 text-xs font-semibold text-slate-600">
	<label>
		Source
		<select
			class="mt-1 block rounded border-slate-300 text-sm"
			bind:value={sourceFilter}
			onchange={load}
		>
			<option value="">All</option>
			<option value="PAYLOAD">PAYLOAD</option>
			<option value="DERIVED">DERIVED</option>
			<option value="SCORE">SCORE</option>
		</select>
	</label>
</div>

{#if error}
	<ErrorNote {error} />
{:else if features}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="features-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Path</th>
					<th class="px-3 py-2">Label</th>
					<th class="px-3 py-2">Type</th>
					<th class="px-3 py-2">Source</th>
					<th class="px-3 py-2">Category</th>
					<th class="px-3 py-2">Active</th>
					{#if canManage}<th class="px-3 py-2"></th>{/if}
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each features as feature (feature.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2 font-mono text-xs">{feature.path}</td>
						<td class="px-3 py-2">{feature.label}</td>
						<td class="px-3 py-2 text-xs">{feature.data_type}</td>
						<td class="px-3 py-2"><Badge value={feature.source} /></td>
						<td class="px-3 py-2 text-xs">{feature.category}</td>
						<td class="px-3 py-2 text-xs">{feature.active ? 'yes' : 'no'}</td>
						{#if canManage}
							<td class="px-3 py-2 text-right">
								<button
									class="text-xs text-blue-700 underline"
									onclick={() => toggleActive(feature)}
								>
									{feature.active ? 'Deactivate' : 'Activate'}
								</button>
							</td>
						{/if}
					</tr>
				{:else}
					<tr><td class="px-3 py-6 text-center text-slate-400" colspan="7">No features</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
