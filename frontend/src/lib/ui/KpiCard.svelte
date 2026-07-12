<script lang="ts">
	import { ArrowDownRight, ArrowUpRight } from '@lucide/svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	let {
		label,
		value,
		delta,
		deltaDirectionGood = 'up',
		loading = false
	}: {
		label: string;
		value: string | number;
		delta?: number;
		deltaDirectionGood?: 'up' | 'down';
		loading?: boolean;
	} = $props();
	const up = $derived((delta ?? 0) >= 0);
	const good = $derived(
		delta === undefined
			? true
			: (up && deltaDirectionGood === 'up') || (!up && deltaDirectionGood === 'down')
	);
</script>

<section class="rounded-card border border-border bg-surface p-4 shadow-card">
	<p class="text-[11px] font-medium uppercase tracking-wide text-text-muted">{label}</p>
	{#if loading}<Skeleton class="mt-3 h-8 w-24" />{:else}<div
			class="mt-2 flex items-end justify-between gap-3"
		>
			<strong class="text-2xl font-semibold tabular-nums text-text">{value}</strong
			>{#if delta !== undefined}<span class={good ? 'text-success' : 'text-danger'}
					>{#if up}<ArrowUpRight size={14} />{:else}<ArrowDownRight size={14} />{/if}<span
						class="text-[11px] tabular-nums">{Math.abs(delta)}%</span
					></span
				>{/if}
		</div>{/if}
</section>
