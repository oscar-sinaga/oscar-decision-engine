<script lang="ts">
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import { flattenDiff } from './diff';
	let { before, after }: { before: unknown; after: unknown } = $props();
	const rows = $derived(flattenDiff(before, after));
	function display(value: unknown) {
		return value === undefined ? '—' : typeof value === 'string' ? value : JSON.stringify(value);
	}
</script>

{#if rows === null}<div class="grid gap-4 md:grid-cols-2">
		<div>
			<h3 class="mb-2 text-xs font-semibold text-text">Before</h3>
			<JsonBlock value={before} />
		</div>
		<div>
			<h3 class="mb-2 text-xs font-semibold text-text">After</h3>
			<JsonBlock value={after} />
		</div>
	</div>{:else if rows.length === 0}<p
		class="rounded-card bg-surface-sunken p-4 text-sm text-text-muted"
	>
		No field-level changes.
	</p>{:else}<div class="overflow-auto rounded-card border border-border">
		<table class="w-full text-xs">
			<thead class="bg-surface-sunken"
				><tr
					><th scope="col" class="px-3 py-2 text-left">Field</th><th
						scope="col"
						class="px-3 py-2 text-left">Before</th
					><th scope="col" class="px-3 py-2 text-left">After</th></tr
				></thead
			><tbody class="divide-y divide-border"
				>{#each rows as row (row.field)}<tr
						><td class="px-3 py-2 font-mono text-text">{row.field}</td><td
							class="bg-danger-bg px-3 py-2 font-mono text-danger">{display(row.before)}</td
						><td class="bg-success-bg px-3 py-2 font-mono text-success">{display(row.after)}</td
						></tr
					>{/each}</tbody
			>
		</table>
	</div>{/if}
