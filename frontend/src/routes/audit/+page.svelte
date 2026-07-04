<script lang="ts">
	import { api } from '$lib/api/client';
	import type { AuditLogItem, Page } from '$lib/api/types';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import { formatDateTime } from '$lib/format';

	let result = $state<Page<AuditLogItem> | null>(null);
	let error = $state<unknown>(null);
	let filters = $state({ event_type: '', entity_type: '', entity_id: '', actor: '' });
	let page = $state(1);
	let expanded = $state<string | null>(null);

	async function load() {
		error = null;
		try {
			result = await api<Page<AuditLogItem>>('/v1/audit-logs', {
				query: { ...filters, page, page_size: 25 }
			});
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
	});
</script>

<h1 class="mb-1 text-xl font-bold text-slate-800">Business Audit Log</h1>
<p class="mb-4 text-sm text-slate-500">
	Append-only governance events — separate from technical logs and decision traces.
</p>

<div class="mb-4 flex flex-wrap items-end gap-3 text-xs font-semibold text-slate-600">
	<label
		>Event type
		<input
			class="mt-1 block rounded border-slate-300 font-mono text-sm"
			placeholder="RULE_VERSION_ACTIVATED"
			bind:value={filters.event_type}
		/>
	</label>
	<label
		>Entity type
		<input
			class="mt-1 block rounded border-slate-300 font-mono text-sm"
			bind:value={filters.entity_type}
		/>
	</label>
	<label
		>Entity ID
		<input
			class="mt-1 block rounded border-slate-300 font-mono text-sm"
			bind:value={filters.entity_id}
		/>
	</label>
	<label
		>Actor
		<input class="mt-1 block rounded border-slate-300 text-sm" bind:value={filters.actor} />
	</label>
	<button
		class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
		onclick={() => {
			page = 1;
			load();
		}}>Search</button
	>
</div>

{#if error}
	<ErrorNote {error} />
{:else if result}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="audit-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Timestamp</th>
					<th class="px-3 py-2">Actor</th>
					<th class="px-3 py-2">Event</th>
					<th class="px-3 py-2">Entity</th>
					<th class="px-3 py-2">Version</th>
					<th class="px-3 py-2">Reason</th>
					<th class="px-3 py-2">Diff</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100 align-top">
				{#each result.items as item (item.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2 text-xs whitespace-nowrap">{formatDateTime(item.created_at)}</td>
						<td class="px-3 py-2 text-xs"
							>{item.actor_label}<span class="block text-[10px] text-slate-400"
								>{item.actor_type}</span
							></td
						>
						<td class="px-3 py-2 font-mono text-[11px]">{item.event_type}</td>
						<td class="px-3 py-2 font-mono text-[11px]"
							>{item.entity_type}<span class="block text-slate-500">{item.entity_id}</span></td
						>
						<td class="px-3 py-2 text-xs">{item.entity_version ?? '—'}</td>
						<td class="px-3 py-2 max-w-56 text-xs text-slate-600">{item.reason ?? '—'}</td>
						<td class="px-3 py-2">
							<button
								class="text-xs text-blue-700 underline"
								onclick={() => (expanded = expanded === item.id ? null : item.id)}
							>
								{expanded === item.id ? 'hide' : 'view'}
							</button>
						</td>
					</tr>
					{#if expanded === item.id}
						<tr>
							<td colspan="7" class="bg-slate-50 px-3 py-2">
								<div class="grid grid-cols-1 gap-2 lg:grid-cols-3">
									<div>
										<h4 class="text-[10px] font-bold text-slate-400 uppercase">Before</h4>
										<JsonBlock value={item.before_value} maxHeight="12rem" />
									</div>
									<div>
										<h4 class="text-[10px] font-bold text-slate-400 uppercase">After</h4>
										<JsonBlock value={item.after_value} maxHeight="12rem" />
									</div>
									<div>
										<h4 class="text-[10px] font-bold text-slate-400 uppercase">
											Metadata (correlation: {item.correlation_id ?? '—'})
										</h4>
										<JsonBlock value={item.metadata} maxHeight="12rem" />
									</div>
								</div>
							</td>
						</tr>
					{/if}
				{:else}
					<tr><td class="px-3 py-6 text-center text-slate-400" colspan="7">No audit events</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
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
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
