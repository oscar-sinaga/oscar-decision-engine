<script lang="ts">
	import type { Meta } from '$lib/api/types';
	import {
		builderConditionToJson,
		type BuilderCondition,
		type BuilderGroup,
		type BuilderLeaf
	} from '$lib/rule-format';
	import FeaturePicker from './FeaturePicker.svelte';

	const emptyLeaf = (): BuilderLeaf => ({
		kind: 'condition',
		field: '',
		operator: '=',
		value: '',
		negated: false
	});
	const emptyGroup = (): BuilderGroup => ({
		kind: 'group',
		logic: 'all',
		children: [emptyLeaf()],
		negated: false
	});

	let {
		meta,
		condition = $bindable<BuilderCondition>(emptyGroup()),
		depth = 0
	}: { meta: Meta | null; condition?: BuilderCondition; depth?: number } = $props();

	function touch() {
		condition = structuredClone(condition);
	}

	function featureFor(leaf: BuilderLeaf) {
		return meta?.features.find((feature) => feature.path === leaf.field);
	}

	function operators(leaf: BuilderLeaf): string[] {
		const type = featureFor(leaf)?.data_type;
		return (type && meta?.operators_by_type[type]) || meta?.operators || ['=', '!='];
	}

	function setField(leaf: BuilderLeaf, field: string) {
		leaf.field = field;
		const type = meta?.features.find((feature) => feature.path === field)?.data_type;
		leaf.operator = (type && meta?.operators_by_type[type]?.[0]) || '=';
		leaf.value = type === 'BOOLEAN' ? false : '';
		touch();
	}

	function setTextValue(leaf: BuilderLeaf, raw: string) {
		const type = featureFor(leaf)?.data_type;
		if (leaf.operator === 'in' || leaf.operator === 'not_in') {
			leaf.value = raw
				.split(',')
				.map((item) => item.trim())
				.filter(Boolean)
				.map((item) => (type === 'NUMBER' ? Number(item) : item));
		} else {
			leaf.value = type === 'NUMBER' && raw !== '' ? Number(raw) : raw;
		}
		touch();
	}

	function textValue(leaf: BuilderLeaf): string {
		return Array.isArray(leaf.value) ? leaf.value.join(', ') : String(leaf.value ?? '');
	}

	function addChild(group: BuilderGroup, child: BuilderCondition) {
		group.children.push(child);
		touch();
	}

	function removeChild(group: BuilderGroup, index: number) {
		if (group.children.length === 1) return;
		group.children.splice(index, 1);
		touch();
	}

	export function toCondition(): Record<string, unknown> {
		return builderConditionToJson(condition);
	}
</script>

{#snippet editor(node: BuilderCondition, level: number, parent?: BuilderGroup, index?: number)}
	{#if node.kind === 'group'}
		<div
			class="space-y-2 rounded border border-slate-200 bg-slate-50 p-3"
			style={`margin-left:${level * 8}px`}
		>
			<div class="flex items-center gap-2">
				<select class="rounded border-slate-300 text-xs" bind:value={node.logic} onchange={touch}>
					<option value="all">ALL (AND)</option>
					<option value="any">ANY (OR)</option>
				</select>
				<label class="flex items-center gap-1 text-xs text-slate-600">
					<input type="checkbox" bind:checked={node.negated} onchange={touch} /> NOT
				</label>
				{#if parent && index !== undefined}
					<button
						class="ml-auto text-xs text-red-600 underline"
						type="button"
						onclick={() => removeChild(parent, index)}>remove group</button
					>
				{/if}
			</div>
			{#each node.children as child, childIndex (childIndex)}
				{@render editor(child, level + 1, node, childIndex)}
			{/each}
			<div class="flex gap-3">
				<button
					class="text-xs font-semibold text-blue-700 underline"
					type="button"
					onclick={() => addChild(node, emptyLeaf())}>+ condition</button
				>
				{#if level < 5}
					<button
						class="text-xs font-semibold text-blue-700 underline"
						type="button"
						onclick={() => addChild(node, emptyGroup())}>+ group</button
					>
				{/if}
			</div>
		</div>
	{:else}
		<div class="flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-white p-2">
			<FeaturePicker
				features={meta?.features ?? []}
				bind:value={node.field}
				onchange={(field) => setField(node, field)}
			/>
			<select
				class="w-28 rounded border-slate-300 text-sm"
				bind:value={node.operator}
				onchange={touch}
			>
				{#each operators(node) as operator (operator)}
					<option value={operator}>{operator}</option>
				{/each}
			</select>
			{#if node.operator !== 'exists' && node.operator !== 'is_null'}
				{#if featureFor(node)?.data_type === 'BOOLEAN'}
					<select
						class="rounded border-slate-300 text-sm"
						value={String(node.value)}
						onchange={(event) => {
							node.value = event.currentTarget.value === 'true';
							touch();
						}}
					>
						<option value="true">true</option><option value="false">false</option>
					</select>
				{:else}
					<input
						class="min-w-36 flex-1 rounded border-slate-300 text-sm"
						type={featureFor(node)?.data_type === 'NUMBER'
							? 'number'
							: featureFor(node)?.data_type === 'DATE'
								? 'date'
								: 'text'}
						placeholder={node.operator === 'in' || node.operator === 'not_in'
							? 'comma-separated values'
							: 'value'}
						value={textValue(node)}
						oninput={(event) => setTextValue(node, event.currentTarget.value)}
					/>
				{/if}
			{/if}
			<label class="flex items-center gap-1 text-xs text-slate-600"
				><input type="checkbox" bind:checked={node.negated} onchange={touch} /> NOT</label
			>
			{#if parent && index !== undefined}
				<button
					class="ml-auto text-xs text-red-600 underline"
					type="button"
					onclick={() => removeChild(parent, index)}>remove</button
				>
			{/if}
		</div>
	{/if}
{/snippet}

{@render editor(condition, depth)}
