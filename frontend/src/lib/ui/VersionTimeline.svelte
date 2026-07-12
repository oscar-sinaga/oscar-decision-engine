<script lang="ts">
	import StatusBadge from './StatusBadge.svelte';
	import { cn } from '$lib/utils';
	let {
		versions,
		selectedId,
		onSelect
	}: {
		versions: { id: string; version: number; status: string; note?: string }[];
		selectedId: string | null;
		onSelect: (id: string) => void;
	} = $props();
</script>

<div class="space-y-2">
	{#each versions as version (version.id)}<button
			type="button"
			class={cn(
				'w-full rounded-card border bg-surface p-3 text-left transition hover:bg-surface-muted',
				version.id === selectedId ? 'border-primary-500 ring-1 ring-primary-500' : 'border-border'
			)}
			onclick={() => onSelect(version.id)}
			><div class="flex items-center justify-between gap-2">
				<span class="font-mono text-xs font-semibold text-text">v{version.version}</span
				><StatusBadge value={version.status} />
			</div>
			{#if version.note}<p class="mt-1 truncate text-[11px] text-text-muted">
					{version.note}
				</p>{/if}</button
		>{/each}
</div>
