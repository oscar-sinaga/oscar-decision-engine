<script lang="ts">
	import type { Meta, ReasonCode } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import type { BuilderAction } from '$lib/rule-format';

	let {
		meta,
		reasonCodes,
		actions = $bindable<BuilderAction[]>([{ type: 'SET_DECISION', decision: 'MANUAL_REVIEW' }])
	}: { meta: Meta | null; reasonCodes: ReasonCode[]; actions?: BuilderAction[] } = $props();

	function touch() {
		actions = structuredClone(actions);
	}

	function outputType(action: BuilderAction): string | undefined {
		return meta?.writable_outputs.find((output) => output.path === action.target)?.data_type;
	}

	function setValue(action: BuilderAction, raw: string) {
		const type = outputType(action);
		action.value = type === 'NUMBER' && raw !== '' ? Number(raw) : raw;
		touch();
	}

	function useExpression(action: BuilderAction, enabled: boolean) {
		if (enabled) {
			delete action.value;
			action.expression = '';
		} else {
			delete action.expression;
			action.value = '';
		}
		touch();
	}

	function resetAction(action: BuilderAction, type: string) {
		for (const key of ['decision', 'reason_code', 'target', 'value', 'expression'] as const)
			delete action[key];
		action.type = type;
		if (type === 'SET_DECISION') action.decision = 'MANUAL_REVIEW';
		touch();
	}
</script>

<div class="space-y-2">
	{#each actions as action, index (index)}
		<div class="flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-white p-2">
			<select
				class="rounded border-slate-300 text-sm"
				value={action.type}
				onchange={(event) => resetAction(action, event.currentTarget.value)}
			>
				{#each meta?.action_types ?? ['SET_OUTPUT', 'SET_DECISION', 'ADD_REASON_CODE', 'ROUTE_MANUAL_REVIEW', 'STOP_EXECUTION', 'CONTINUE'] as type (type)}
					<option value={type}>{type}</option>
				{/each}
			</select>
			{#if action.type === 'SET_OUTPUT'}
				<select
					class="min-w-56 rounded border-slate-300 text-sm"
					bind:value={action.target}
					onchange={touch}
				>
					<option value={undefined}>— output —</option>
					{#each meta?.writable_outputs ?? [] as output (output.path)}
						<option value={output.path}>{output.label} · {output.data_type}</option>
					{/each}
				</select>
				{#if auth.hasPermission('rule.author_expression')}
					<label class="flex items-center gap-1 text-xs text-slate-600">
						<input
							type="checkbox"
							checked={action.expression !== undefined}
							onchange={(event) => useExpression(action, event.currentTarget.checked)}
						/> expression
					</label>
				{/if}
				{#if action.expression !== undefined}
					<input
						class="min-w-64 flex-1 rounded border-slate-300 font-mono text-sm"
						bind:value={action.expression}
						oninput={touch}
						placeholder="loan.requested_amount * 0.8"
					/>
				{:else if outputType(action) === 'BOOLEAN'}
					<select
						class="rounded border-slate-300 text-sm"
						value={String(action.value ?? false)}
						onchange={(event) => {
							action.value = event.currentTarget.value === 'true';
							touch();
						}}><option value="true">true</option><option value="false">false</option></select
					>
				{:else}
					<input
						class="min-w-36 flex-1 rounded border-slate-300 text-sm"
						type={outputType(action) === 'NUMBER'
							? 'number'
							: outputType(action) === 'DATE'
								? 'date'
								: 'text'}
						value={String(action.value ?? '')}
						oninput={(event) => setValue(action, event.currentTarget.value)}
						placeholder="output value"
					/>
				{/if}
			{:else if action.type === 'SET_DECISION' || action.type === 'STOP_EXECUTION'}
				<select
					class="rounded border-slate-300 text-sm"
					bind:value={action.decision}
					onchange={touch}
				>
					<option value={undefined}>— no decision —</option>
					{#each meta?.decisions ?? [] as decision (decision)}<option value={decision}
							>{decision}</option
						>{/each}
				</select>
			{/if}
			{#if action.type !== 'SET_OUTPUT'}
				<select
					class="min-w-48 rounded border-slate-300 text-sm"
					bind:value={action.reason_code}
					onchange={touch}
				>
					<option value={undefined}>— no reason —</option>
					{#each reasonCodes as reason (reason.code)}<option value={reason.code}
							>{reason.code}</option
						>{/each}
				</select>
			{/if}
			<button
				class="ml-auto text-xs text-red-600 underline"
				type="button"
				onclick={() => (actions = actions.filter((_, i) => i !== index))}
				disabled={actions.length === 1}>remove</button
			>
		</div>
	{/each}
	<button
		class="text-xs font-semibold text-blue-700 underline"
		type="button"
		onclick={() => (actions = [...actions, { type: 'CONTINUE' }])}>+ action</button
	>
</div>
