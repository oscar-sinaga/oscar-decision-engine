<script lang="ts">
	import { AlertTriangle, Check, ChevronDown, ChevronRight, CircleDashed } from '@lucide/svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import type { TraceStep } from '$lib/api/types';
	import JsonBlock from '$lib/components/JsonBlock.svelte';

	let { steps }: { steps: TraceStep[] } = $props();
	const expanded = new SvelteSet<number>();

	function toggle(order: number): void {
		if (expanded.has(order)) expanded.delete(order);
		else expanded.add(order);
	}

	function tone(status: string): 'danger' | 'warning' | 'success' {
		const normalized = status.toUpperCase();
		return normalized.includes('ERROR') || normalized.includes('FAIL')
			? 'danger'
			: normalized.includes('SKIP')
				? 'warning'
				: 'success';
	}
</script>

<div class="space-y-0" data-testid="trace-steps">
	{#each steps as step (step.order)}
		{@const stepTone = tone(step.status)}
		<article class="relative grid grid-cols-[24px_1fr] gap-3 pb-5">
			<div class="flex flex-col items-center">
				<span
					class="z-10 flex size-6 items-center justify-center rounded-full {stepTone === 'success'
						? 'bg-success-bg text-success'
						: stepTone === 'danger'
							? 'bg-danger-bg text-danger'
							: 'bg-warning-bg text-warning'}"
				>
					{#if stepTone === 'success'}
						<Check size={13} />
					{:else if stepTone === 'danger'}
						<AlertTriangle size={13} />
					{:else}
						<CircleDashed size={13} />
					{/if}
				</span>
				<span class="mt-1 h-full w-px bg-border"></span>
			</div>
			<div class="min-w-0 rounded-card border border-border bg-surface shadow-card">
				<button
					type="button"
					class="flex w-full items-center gap-3 px-3 py-2 text-left"
					onclick={() => toggle(step.order)}
				>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm font-semibold text-text">{step.name}</span>
						<span class="font-mono text-[11px] text-text-muted">
							{step.node_key ?? step.type}{step.taken_edge ? ` → ${step.taken_edge}` : ''}
						</span>
					</span>
					<span class="font-mono text-[11px] tabular-nums text-text-muted">
						{step.duration_ms.toFixed(1)} ms
					</span>
					{#if expanded.has(step.order)}
						<ChevronDown size={15} />
					{:else}
						<ChevronRight size={15} />
					{/if}
				</button>
				{#if expanded.has(step.order)}
					<div class="border-t border-border p-3">
						<JsonBlock value={step} />
					</div>
				{/if}
			</div>
		</article>
	{/each}
</div>
