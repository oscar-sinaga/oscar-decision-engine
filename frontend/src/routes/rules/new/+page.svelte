<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import type { Meta, ReasonCode, Rule } from '$lib/api/types';
	import Card from '$lib/components/Card.svelte';
	import ConditionBuilder from '$lib/components/ConditionBuilder.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';

	let meta = $state<Meta | null>(null);
	let reasonCodes = $state<ReasonCode[]>([]);
	let error = $state<unknown>(null);
	let builder = $state<ReturnType<typeof ConditionBuilder> | null>(null);

	let form = $state({
		rule_code: '',
		name: '',
		description: '',
		category: 'ELIGIBILITY',
		decision: 'MANUAL_REVIEW',
		reason_code: '',
		version_note: ''
	});
	let preview = $state<Record<string, unknown>>({});

	$effect(() => {
		api<Meta>('/v1/meta')
			.then((m) => (meta = m))
			.catch(() => {});
		api<ReasonCode[]>('/v1/reason-codes')
			.then((rc) => (reasonCodes = rc))
			.catch(() => {});
	});

	function refreshPreview() {
		preview = {
			condition: builder?.toCondition() ?? {},
			action: { decision: form.decision, reason_code: form.reason_code || null }
		};
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		try {
			const rule = await api<Rule>('/v1/rules', {
				body: {
					rule_code: form.rule_code,
					name: form.name,
					description: form.description,
					category: form.category,
					condition: builder?.toCondition() ?? {},
					action: { decision: form.decision, reason_code: form.reason_code || null },
					version_note: form.version_note
				}
			});
			goto(`/rules/${rule.id}`);
		} catch (err) {
			error = err;
		}
	}
</script>

<a class="text-xs text-blue-700 underline" href="/rules">← Back to rules</a>
<h1 class="mt-2 mb-4 text-xl font-bold text-slate-800">Create rule</h1>

<form class="grid grid-cols-1 gap-4 xl:grid-cols-2" onsubmit={submit} oninput={refreshPreview}>
	<div class="space-y-4">
		<Card title="General information">
			<div class="grid grid-cols-2 gap-3 text-xs font-semibold text-slate-600">
				<label
					>Rule code
					<input
						class="mt-1 w-full rounded border-slate-300 font-mono text-sm"
						placeholder="VEHICLE_AGE_MAX_MOTOR"
						bind:value={form.rule_code}
						required
					/></label
				>
				<label
					>Name
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.name}
						required
					/></label
				>
				<label
					>Category
					<select class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={form.category}>
						{#each meta?.rule_categories ?? [] as category (category)}
							<option value={category}>{category}</option>
						{/each}
					</select></label
				>
				<label
					>Version note
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.version_note}
					/></label
				>
				<label class="col-span-2"
					>Description
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.description}
					/></label
				>
			</div>
		</Card>

		<Card title="Conditions">
			<ConditionBuilder bind:this={builder} {meta} />
		</Card>

		<Card title="Action when matched">
			<div class="grid grid-cols-2 gap-3 text-xs font-semibold text-slate-600">
				<label
					>Decision
					<select class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={form.decision}>
						{#each meta?.decisions ?? [] as decision (decision)}
							<option value={decision}>{decision}</option>
						{/each}
					</select></label
				>
				<label
					>Reason code
					<select
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.reason_code}
					>
						<option value="">— none —</option>
						{#each reasonCodes as rc (rc.code)}
							<option value={rc.code}>{rc.code}</option>
						{/each}
					</select></label
				>
			</div>
		</Card>

		{#if error}
			<ErrorNote {error} />
		{/if}

		<button
			class="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
			type="submit">Create draft rule</button
		>
	</div>

	<Card title="Generated definition (preview)">
		<JsonBlock value={preview} />
	</Card>
</form>
