<script lang="ts">
	import type { Snippet } from 'svelte';
	import { RotateCcw } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	let { children, onReset }: { children: Snippet; onReset?: () => void } = $props();
</script>

<section
	class="mb-4 flex flex-wrap items-end gap-3 rounded-card border border-border bg-surface p-3 shadow-card"
>
	<div class="flex min-w-0 flex-1 flex-wrap items-end gap-3">{@render children()}</div>
	{#if onReset}<Button variant="ghost" size="sm" onclick={onReset}
			><RotateCcw size={14} />Reset</Button
		>{/if}
</section>
