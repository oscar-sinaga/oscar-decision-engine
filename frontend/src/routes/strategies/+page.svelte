<script lang="ts">
	import { api } from '$lib/api/client';
	import type { Strategy } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';

	let strategies = $state<Strategy[] | null>(null);
	let error = $state<unknown>(null);

	$effect(() => {
		api<Strategy[]>('/v1/strategies')
			.then((s) => (strategies = s))
			.catch((err) => (error = err));
	});
</script>

<h1 class="mb-4 text-xl font-bold text-slate-800">Strategies</h1>

{#if error}
	<ErrorNote {error} />
{:else if strategies}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="strategies-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Strategy code</th>
					<th class="px-3 py-2">Name</th>
					<th class="px-3 py-2">Product</th>
					<th class="px-3 py-2">Segment</th>
					<th class="px-3 py-2">Active version</th>
					<th class="px-3 py-2">Latest</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each strategies as strategy (strategy.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2">
							<a class="font-mono text-xs text-blue-700 underline" href="/strategies/{strategy.id}">
								{strategy.strategy_code}
							</a>
						</td>
						<td class="px-3 py-2">{strategy.name}</td>
						<td class="px-3 py-2 text-xs">{strategy.product_type}</td>
						<td class="px-3 py-2 text-xs">{strategy.segment}</td>
						<td class="px-3 py-2"
							>{strategy.active_version ? `v${strategy.active_version}` : '—'}</td
						>
						<td class="px-3 py-2">
							{#if strategy.latest_version}
								v{strategy.latest_version}
								{#if strategy.latest_status}<Badge value={strategy.latest_status} />{/if}
							{:else}—{/if}
						</td>
					</tr>
				{:else}
					<tr><td class="px-3 py-6 text-center text-slate-400" colspan="6">No strategies</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
