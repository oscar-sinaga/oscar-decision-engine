<script lang="ts">
	// Guided condition builder (docs/09 §5): field/operator/value rows with
	// ALL/ANY logic. Values are JSON-typed (numbers, booleans, lists, strings).
	import type { Meta } from '$lib/api/types';

	export interface BuilderRow {
		field: string;
		operator: string;
		value: string;
	}

	let {
		meta,
		logic = $bindable('all'),
		rows = $bindable<BuilderRow[]>([{ field: '', operator: '>', value: '' }])
	}: { meta: Meta | null; logic?: string; rows?: BuilderRow[] } = $props();

	function parseValue(raw: string): unknown {
		const trimmed = raw.trim();
		if (trimmed === '') return null;
		try {
			return JSON.parse(trimmed);
		} catch {
			return trimmed; // plain string value
		}
	}

	export function toCondition(): Record<string, unknown> {
		return {
			[logic]: rows
				.filter((row) => row.field)
				.map((row) => ({
					field: row.field,
					operator: row.operator,
					...(row.operator === 'exists' || row.operator === 'is_null'
						? {}
						: { value: parseValue(row.value) })
				}))
		};
	}
</script>

<div class="space-y-2">
	<label class="text-xs font-semibold text-slate-600">
		Match
		<select class="ml-2 rounded border-slate-300 text-sm" bind:value={logic}>
			<option value="all">ALL conditions (AND)</option>
			<option value="any">ANY condition (OR)</option>
		</select>
	</label>

	{#each rows as row, index (index)}
		<div class="flex items-center gap-2">
			<select class="w-72 rounded border-slate-300 text-sm" bind:value={row.field}>
				<option value="">— select feature —</option>
				{#each meta?.features ?? [] as feature (feature.path)}
					<option value={feature.path}>{feature.path}</option>
				{/each}
			</select>
			<select class="w-28 rounded border-slate-300 text-sm" bind:value={row.operator}>
				{#each meta?.operators ?? ['=', '!=', '>', '>=', '<', '<='] as op (op)}
					<option value={op}>{op}</option>
				{/each}
			</select>
			{#if row.operator !== 'exists' && row.operator !== 'is_null'}
				<input
					class="flex-1 rounded border-slate-300 font-mono text-sm"
					placeholder="value, e.g. 0.45, &quot;MOTOR&quot;, [1, 2]"
					bind:value={row.value}
				/>
			{/if}
			<button
				class="text-xs text-red-600 underline"
				type="button"
				onclick={() => (rows = rows.filter((_, i) => i !== index))}>remove</button
			>
		</div>
	{/each}

	<button
		class="text-xs font-semibold text-blue-700 underline"
		type="button"
		onclick={() => (rows = [...rows, { field: '', operator: '>', value: '' }])}
	>
		+ add condition
	</button>
</div>
