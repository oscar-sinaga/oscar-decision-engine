<script lang="ts">
	import { ApiError } from '$lib/api/client';

	let { error }: { error: unknown } = $props();

	const message = $derived(
		error instanceof ApiError
			? `${error.code}: ${error.message}${error.detailText ? ` — ${error.detailText}` : ''}`
			: error instanceof Error
				? error.message
				: String(error)
	);
	const correlation = $derived(error instanceof ApiError ? error.correlationId : null);
</script>

<div class="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
	{message}
	{#if correlation}
		<span class="mt-1 block text-xs text-red-500">correlation: {correlation}</span>
	{/if}
</div>
