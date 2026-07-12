<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';
	import { cn } from '$lib/utils';
	import type { StrategyFlowNode } from './types';

	let { data, selected }: NodeProps<StrategyFlowNode> = $props();
	const isCondition = $derived(data.nodeType === 'CONDITION');
	const isTerminal = $derived(data.nodeType === 'START' || data.nodeType === 'END');
	const icon = $derived(
		(
			{
				START: '▶',
				END: '■',
				VALIDATION: '✓',
				CALCULATION: '∑',
				RULE_SET: 'R',
				SCORECARD: '#',
				DECISION_TABLE: '▦',
				CONDITION: '?'
			} as Record<string, string>
		)[data.nodeType] ?? '•'
	);
	const tone = $derived(
		(
			{
				START: 'border-success/40 bg-success-bg',
				END: 'border-neutral/40 bg-neutral-bg',
				VALIDATION: 'border-info/40 bg-info-bg',
				CALCULATION: 'border-special/40 bg-special-bg',
				RULE_SET: 'border-primary-500/40 bg-primary-50',
				SCORECARD: 'border-warning/40 bg-warning-bg',
				DECISION_TABLE: 'border-success/40 bg-success-bg',
				CONDITION: 'border-special/40 bg-special-bg'
			} as Record<string, string>
		)[data.nodeType] ?? 'border-border bg-surface'
	);
</script>

<div
	class:rotate-45={isCondition}
	class={cn(
		'min-w-40 rounded-card border px-3 py-2 shadow-card transition',
		tone,
		selected && 'ring-2 ring-primary-500 ring-offset-2',
		data.invalid && 'border-danger ring-2 ring-danger/20',
		isTerminal && 'rounded-full'
	)}
>
	<Handle type="target" position={Position.Left} />
	<div class:-rotate-45={isCondition} class="space-y-1">
		<div class="flex items-center gap-2">
			<span
				class="grid h-6 w-6 place-items-center rounded-control bg-surface/80 text-xs font-bold text-text"
				>{icon}</span
			>
			<div class="min-w-0">
				<div class="truncate text-xs font-semibold text-text">{data.name || data.nodeType}</div>
				<div class="text-[10px] uppercase tracking-wide text-text-muted">{data.nodeType}</div>
			</div>
		</div>
		{#if data.referenceCode}<div
				class="truncate rounded-control bg-surface/75 px-1.5 py-0.5 font-mono text-[10px] text-primary-700"
			>
				{data.referenceCode}
			</div>{/if}
		{#if !isTerminal}<div class="text-[10px] text-text-muted">on error: {data.onError}</div>{/if}
	</div>
	{#if data.nodeType !== 'END'}
		{#if isCondition}
			<Handle
				id="TRUE"
				type="source"
				position={Position.Right}
				style="top:35%;background:var(--color-success)"
			/>
			<Handle
				id="FALSE"
				type="source"
				position={Position.Right}
				style="top:68%;background:var(--color-danger)"
			/>
		{:else}
			<Handle type="source" position={Position.Right} />
		{/if}
	{/if}
</div>
