<script lang="ts">
	import { api } from '$lib/api/client';
	import type { ConfigEntity } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';

	let tables = $state<ConfigEntity[] | null>(null);
	let error = $state<unknown>(null);
	let creating = $state(false);
	let submitting = $state(false);
	let code = $state('');
	let name = $state('');
	let description = $state('');

	async function load() {
		error = null;
		try {
			tables = await api<ConfigEntity[]>('/v1/decision-tables');
		} catch (err) {
			error = err;
		}
	}

	function latestRowCount(table: ConfigEntity): number {
		const rows = table.versions.at(-1)?.config.rows;
		return Array.isArray(rows) ? rows.length : 0;
	}

	async function createTable() {
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
			window.location.href = `/decision-tables/${created.id}`;
		} catch (err) {
			error = err;
		} finally {
			submitting = false;
		}
	}

	$effect(() => {
		load();
	});
</script>

<div class="mb-4 flex items-center justify-between">
	<div>
		<h1 class="text-xl font-bold text-slate-800">Decision Tables</h1>
		<p class="text-sm text-slate-500">Author ordered policy matrices without editing JSON.</p>
	</div>
	{#if auth.hasPermission('rule.create')}
		<button
			class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
			onclick={() => (creating = !creating)}
		>
			{creating ? 'Close' : 'New decision table'}
		</button>
	{/if}
</div>

{#if error}<div class="mb-4"><ErrorNote {error} /></div>{/if}

{#if creating}
	<div class="mb-4">
		<Card title="Create decision table">
			<form
				class="grid gap-3 md:grid-cols-2"
				onsubmit={(event) => {
					event.preventDefault();
					createTable();
				}}
			>
				<label class="text-xs font-semibold text-slate-600">
					Code
					<input
						class="mt-1 block w-full rounded border-slate-300 text-sm"
						bind:value={code}
						required
						minlength="3"
					/>
				</label>
				<label class="text-xs font-semibold text-slate-600">
					Name
					<input
						class="mt-1 block w-full rounded border-slate-300 text-sm"
						bind:value={name}
						required
					/>
				</label>
				<label class="text-xs font-semibold text-slate-600 md:col-span-2">
					Description
					<textarea
						class="mt-1 block w-full rounded border-slate-300 text-sm"
						rows="2"
						bind:value={description}></textarea>
				</label>
				<div class="md:col-span-2">
					<button
						class="rounded bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
						disabled={submitting}
					>
						{submitting ? 'Creating…' : 'Create and open grid'}
					</button>
				</div>
			</form>
		</Card>
	</div>
{/if}

{#if tables}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="decision-tables-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Code</th>
					<th class="px-3 py-2">Name</th>
					<th class="px-3 py-2">Active version</th>
					<th class="px-3 py-2">Latest</th>
					<th class="px-3 py-2">Rows</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each tables as table (table.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2">
							<a
								class="font-mono text-xs text-blue-700 underline"
								href="/decision-tables/{table.id}">{table.code}</a
							>
						</td>
						<td class="px-3 py-2">{table.name}</td>
						<td class="px-3 py-2">{table.active_version ? `v${table.active_version}` : '—'}</td>
						<td class="px-3 py-2">v{table.latest_version} <Badge value={table.latest_status} /></td>
						<td class="px-3 py-2 text-xs text-slate-500">
							{latestRowCount(table)}
						</td>
					</tr>
				{:else}
					<tr
						><td class="px-3 py-6 text-center text-slate-400" colspan="5">No decision tables</td
						></tr
					>
				{/each}
			</tbody>
		</table>
	</div>
{:else if !error}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
