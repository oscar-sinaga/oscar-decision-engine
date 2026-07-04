<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title = '',
		children,
		actions
	}: { title?: string; children: Snippet; actions?: Snippet } = $props();
</script>

<section class="rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if title || actions}
		<header class="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
			<h2 class="text-sm font-semibold text-slate-700">{title}</h2>
			{#if actions}{@render actions()}{/if}
		</header>
	{/if}
	<div class="p-4">
		{@render children()}
	</div>
</section>
