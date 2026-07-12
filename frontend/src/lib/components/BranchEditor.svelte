<script lang="ts">
	import type { Meta, ReasonCode } from '$lib/api/types';
	import type { BuilderAction, BuilderBranch, BuilderGroup } from '$lib/rule-format';
	import ActionListEditor from './ActionListEditor.svelte';
	import ConditionBuilder from './ConditionBuilder.svelte';

	const condition = (): BuilderGroup => ({
		kind: 'group',
		logic: 'all',
		negated: false,
		children: [{ kind: 'condition', field: '', operator: '=', value: '', negated: false }]
	});
	const branch = (): BuilderBranch => ({
		when: condition(),
		then: [{ type: 'SET_DECISION', decision: 'MANUAL_REVIEW' }]
	});

	let {
		meta,
		reasonCodes,
		branches = $bindable<BuilderBranch[]>([branch()]),
		defaultActions = $bindable<BuilderAction[] | null>(null)
	}: {
		meta: Meta | null;
		reasonCodes: ReasonCode[];
		branches?: BuilderBranch[];
		defaultActions?: BuilderAction[] | null;
	} = $props();

	function move(index: number, delta: number) {
		const target = index + delta;
		if (target < 0 || target >= branches.length) return;
		const copy = [...branches];
		[copy[index], copy[target]] = [copy[target], copy[index]];
		branches = copy;
	}
</script>

<div class="space-y-3">
	{#each branches as item, index (index)}
		<section class="space-y-3 rounded-card border border-border-strong p-3">
			<header class="flex items-center gap-2 text-xs font-bold text-text-muted">
				<span>WHEN · branch {index + 1}</span>
				<button
					class="ml-auto underline"
					type="button"
					onclick={() => move(index, -1)}
					disabled={index === 0}>↑</button
				>
				<button
					class="underline"
					type="button"
					onclick={() => move(index, 1)}
					disabled={index === branches.length - 1}>↓</button
				>
				<button
					class="text-danger underline"
					type="button"
					onclick={() => (branches = branches.filter((_, i) => i !== index))}
					disabled={branches.length === 1}>remove</button
				>
			</header>
			<ConditionBuilder {meta} bind:condition={item.when} />
			<div class="text-xs font-bold text-text-muted">THEN</div>
			<ActionListEditor {meta} {reasonCodes} bind:actions={item.then} />
		</section>
	{/each}
	<button
		class="text-xs font-semibold text-primary-700 underline"
		type="button"
		onclick={() => (branches = [...branches, branch()])}>+ branch</button
	>

	<section class="space-y-2 rounded-card border border-dashed border-border-strong p-3">
		<label class="flex items-center gap-2 text-xs font-bold text-text-muted">
			<input
				type="checkbox"
				checked={defaultActions !== null}
				onchange={(event) =>
					(defaultActions = event.currentTarget.checked ? [{ type: 'CONTINUE' }] : null)}
			/> Enable ELSE
		</label>
		{#if defaultActions}
			<ActionListEditor {meta} {reasonCodes} bind:actions={defaultActions} />
		{/if}
	</section>
</div>
