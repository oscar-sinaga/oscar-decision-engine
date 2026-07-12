<script lang="ts">
	import { AlertTriangle } from '@lucide/svelte';
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

<div
	class="flex gap-2 rounded-card border border-danger/20 bg-danger-bg px-3 py-2 text-sm text-danger"
	role="alert"
>
	<AlertTriangle class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
	<div>
		<div>{message}</div>
		{#if correlation}<span class="mt-1 block font-mono text-[11px] opacity-75"
				>correlation: {correlation}</span
			>{/if}
	</div>
</div>
