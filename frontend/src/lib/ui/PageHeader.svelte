<script lang="ts">
	import type { Snippet } from 'svelte';
	let { title, description, actions }: { title: string; description?: string; actions?: Snippet } =
		$props();
</script>

<header class="mb-4 flex flex-wrap items-start justify-between gap-4">
	<div>
		<h1 class="text-lg font-semibold text-text">{title}</h1>
		{#if description}<p class="mt-1 text-xs text-text-muted">{description}</p>{/if}
	</div>
	{#if actions}<div class="flex items-center gap-2">{@render actions()}</div>{/if}
</header>
