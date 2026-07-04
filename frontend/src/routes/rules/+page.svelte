<script lang="ts">
	import { api } from '$lib/api/client';
	import type { Meta, Rule } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { auth } from '$lib/auth.svelte';

	let rules = $state<Rule[] | null>(null);
	let meta = $state<Meta | null>(null);
	let error = $state<unknown>(null);
	let category = $state('');

	async function load() {
		error = null;
		try {
			rules = await api<Rule[]>('/v1/rules', { query: { category: category || undefined } });
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

<div class="mb-4 flex items-center justify-between">
	<h1 class="text-xl font-bold text-slate-800">Rules</h1>
	{#if auth.hasPermission('rule.create')}
		<a
			class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
			href="/rules/new">New rule</a
		>
	{/if}
</div>

<div class="mb-4 flex items-end gap-3 text-xs font-semibold text-slate-600">
	<label>
		Category
		<select class="mt-1 block rounded border-slate-300 text-sm" bind:value={category}>
			<option value="">All</option>
			{#each meta?.rule_categories ?? [] as item (item)}
				<option value={item}>{item}</option>
			{/each}
		</select>
	</label>
	<button
		class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
		onclick={load}>Filter</button
	>
</div>

{#if error}
	<ErrorNote {error} />
{:else if rules}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="rules-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Rule code</th>
					<th class="px-3 py-2">Name</th>
					<th class="px-3 py-2">Category</th>
					<th class="px-3 py-2">Owner</th>
					<th class="px-3 py-2">Active version</th>
					<th class="px-3 py-2">Latest</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each rules as rule (rule.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2">
							<a class="font-mono text-xs text-blue-700 underline" href="/rules/{rule.id}">
								{rule.rule_code}
							</a>
						</td>
						<td class="px-3 py-2">{rule.name}</td>
						<td class="px-3 py-2 text-xs">{rule.category}</td>
						<td class="px-3 py-2 text-xs">{rule.owner_team}</td>
						<td class="px-3 py-2">{rule.active_version ? `v${rule.active_version}` : '—'}</td>
						<td class="px-3 py-2">
							v{rule.latest_version}
							<Badge value={rule.latest_status} />
						</td>
					</tr>
				{:else}
					<tr><td class="px-3 py-6 text-center text-slate-400" colspan="6">No rules</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
