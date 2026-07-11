<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';
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
</script>

<div
	class:rotate-45={isCondition}
	class="min-w-40 rounded-xl border bg-white px-3 py-2 shadow-sm transition {selected
		? 'border-blue-500 ring-2 ring-blue-100'
		: data.invalid
			? 'border-red-500 ring-2 ring-red-100'
			: 'border-slate-300'} {isTerminal ? 'rounded-full' : ''}"
>
	<Handle type="target" position={Position.Left} />
	<div class:-rotate-45={isCondition} class="space-y-1">
		<div class="flex items-center gap-2">
			<span class="grid h-6 w-6 place-items-center rounded bg-slate-100 text-xs font-bold"
				>{icon}</span
			>
			<div class="min-w-0">
				<div class="truncate text-xs font-semibold text-slate-800">
					{data.name || data.nodeType}
				</div>
				<div class="text-[10px] uppercase tracking-wide text-slate-400">{data.nodeType}</div>
			</div>
		</div>
		{#if data.referenceCode}
			<div class="truncate rounded bg-blue-50 px-1.5 py-0.5 font-mono text-[10px] text-blue-700">
				{data.referenceCode}
			</div>
		{/if}
		{#if !isTerminal}
			<div class="text-[10px] text-slate-400">on error: {data.onError}</div>
		{/if}
	</div>
	{#if data.nodeType !== 'END'}
		{#if isCondition}
			<Handle
				id="TRUE"
				type="source"
				position={Position.Right}
				style="top:35%;background:#16a34a"
			/>
			<Handle
				id="FALSE"
				type="source"
				position={Position.Right}
				style="top:68%;background:#dc2626"
			/>
		{:else}
			<Handle type="source" position={Position.Right} />
		{/if}
	{/if}
</div>
