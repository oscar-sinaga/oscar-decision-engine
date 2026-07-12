<script lang="ts">
	import { Inbox } from '@lucide/svelte';
	import type { Component } from 'svelte';
	import { Button } from '$lib/components/ui/button';

	let {
		icon: Icon = Inbox,
		title,
		hint,
		actionLabel,
		onAction
	}: {
		icon?: Component;
		title: string;
		hint?: string;
		actionLabel?: string;
		onAction?: () => void;
	} = $props();
</script>

<div class="flex flex-col items-center justify-center px-6 py-12 text-center">
	<div
		class="mb-3 flex size-12 items-center justify-center rounded-full bg-surface-sunken text-text-muted"
	>
		<Icon size={22} />
	</div>
	<h3 class="text-sm font-semibold text-text">{title}</h3>
	{#if hint}
		<p class="mt-1 max-w-sm text-xs text-text-muted">{hint}</p>
	{/if}
	{#if actionLabel && onAction}
		<Button class="mt-4" size="sm" onclick={onAction}>{actionLabel}</Button>
	{/if}
</div>
