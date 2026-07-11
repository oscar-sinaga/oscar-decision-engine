<script lang="ts">
	import type { Meta } from '$lib/api/types';

	let {
		features,
		value = $bindable(''),
		onchange = () => {}
	}: { features: Meta['features']; value?: string; onchange?: (value: string) => void } = $props();

	let selected = $derived(features.find((feature) => feature.path === value));
	let listId = `features-${Math.random().toString(36).slice(2)}`;
</script>

<div class="flex min-w-64 items-center gap-2">
	<input
		class="min-w-0 flex-1 rounded border-slate-300 text-sm"
		list={listId}
		placeholder="Search feature path, label, or category"
		bind:value
		oninput={() => onchange(value)}
	/>
	<datalist id={listId}>
		{#each features as feature (feature.path)}
			<option value={feature.path}>{feature.label} · {feature.category}</option>
		{/each}
	</datalist>
	{#if selected}
		<span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
			{selected.data_type}
		</span>
	{/if}
</div>
