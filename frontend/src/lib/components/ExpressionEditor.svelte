<script lang="ts">
	import { api } from '$lib/api/client';
	import type { Meta } from '$lib/api/types';

	interface ValidationResult {
		valid: true;
		inferred_type: string;
		referenced_features: string[];
		normalized_preview: string;
		ast_node_count: number;
	}

	let {
		meta,
		expression = $bindable(''),
		outputTarget = $bindable('')
	}: { meta: Meta | null; expression?: string; outputTarget?: string } = $props();
	let validation = $state<ValidationResult | null>(null);
	let validationError = $state('');
	let validating = $state(false);
	let featureToInsert = $state('');

	$effect(() => {
		const text = expression.trim();
		validation = null;
		validationError = '';
		if (!text) return;
		const timer = window.setTimeout(async () => {
			validating = true;
			try {
				validation = await api<ValidationResult>('/v1/expressions/validate', {
					body: { expression: text, expects: 'value' }
				});
			} catch (error) {
				validationError = error instanceof Error ? error.message : 'Expression validation failed';
			} finally {
				validating = false;
			}
		}, 350);
		return () => window.clearTimeout(timer);
	});

	function insertFeature() {
		if (!featureToInsert) return;
		expression = `${expression}${expression && !expression.endsWith(' ') ? ' ' : ''}${featureToInsert}`;
	}
</script>

<div class="space-y-3">
	<label class="block text-xs font-semibold text-slate-600">
		Output target
		<select class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={outputTarget} required>
			<option value="">— choose writable output —</option>
			{#each meta?.writable_outputs ?? [] as output (output.path)}
				<option value={output.path}>{output.label} · {output.path} · {output.data_type}</option>
			{/each}
		</select>
	</label>
	<div class="flex gap-2">
		<select class="min-w-0 flex-1 rounded border-slate-300 text-sm" bind:value={featureToInsert}>
			<option value="">— insert catalog feature —</option>
			{#each meta?.features ?? [] as feature (feature.path)}
				<option value={feature.path}>{feature.path} · {feature.data_type}</option>
			{/each}
		</select>
		<button
			class="rounded bg-slate-200 px-3 text-xs font-semibold"
			type="button"
			onclick={insertFeature}>Insert</button
		>
	</div>
	<label class="block text-xs font-semibold text-slate-600">
		OSCAR expression
		<textarea
			class="mt-1 min-h-40 w-full rounded border-slate-300 font-mono text-sm"
			bind:value={expression}
			maxlength="2000"
			placeholder="CASE WHEN loan.ltv > 0.85 THEN 0 ELSE loan.requested_amount * 0.8 END"
			required></textarea>
	</label>
	<div class="text-xs">
		{#if validating}<span class="text-slate-500">Validating…</span>
		{:else if validation}<span class="font-semibold text-emerald-700">
				Valid · {validation.inferred_type} · {validation.ast_node_count} AST nodes
			</span>
		{:else if validationError}<span class="font-semibold text-red-700">{validationError}</span>{/if}
	</div>
	{#if validation?.referenced_features.length}
		<p class="text-xs text-slate-500">References: {validation.referenced_features.join(', ')}</p>
	{/if}
</div>
