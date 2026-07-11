<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import type { Meta, ReasonCode, Rule } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import BranchEditor from '$lib/components/BranchEditor.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import {
		builderToJson,
		humanPreview,
		type BuilderAction,
		type BuilderBranch,
		type BuilderState
	} from '$lib/rule-format';

	let meta = $state<Meta | null>(null);
	let reasonCodes = $state<ReasonCode[]>([]);
	let error = $state<unknown>(null);
	let tab = $state<'human' | 'json'>('human');
	let branches = $state<BuilderBranch[]>([
		{
			when: {
				kind: 'group',
				logic: 'all',
				negated: false,
				children: [{ kind: 'condition', field: '', operator: '=', value: '', negated: false }]
			},
			then: [{ type: 'SET_DECISION', decision: 'MANUAL_REVIEW' }]
		}
	]);
	let defaultActions = $state<BuilderAction[] | null>(null);
	let form = $state({
		rule_code: '',
		name: '',
		description: '',
		category: 'ELIGIBILITY',
		rule_kind: 'POLICY_OUTCOME',
		version_note: ''
	});

	let builderState = $derived<BuilderState>({
		form: 'branched',
		ruleKind: form.rule_kind,
		branches,
		defaultActions
	});
	let preview = $derived(builderToJson(builderState));

	$effect(() => {
		api<Meta>('/v1/meta')
			.then((value) => {
				meta = value;
				if (!value.rule_categories.some((category) => category.code === form.category)) {
					form.category = value.rule_categories[0]?.code ?? '';
				}
			})
			.catch(() => {});
		api<ReasonCode[]>('/v1/reason-codes')
			.then((value) => (reasonCodes = value))
			.catch(() => {});
	});

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		try {
			const definition = builderToJson(builderState);
			const rule = await api<Rule>('/v1/rules', {
				body: { ...form, ...definition }
			});
			goto(`/rules/${rule.id}`);
		} catch (err) {
			error = err;
		}
	}
</script>

<a class="text-xs text-blue-700 underline" href="/rules">← Back to rules</a>
<h1 class="mt-2 mb-4 text-xl font-bold text-slate-800">Create rule</h1>

<form class="grid grid-cols-1 gap-4 xl:grid-cols-2" onsubmit={submit}>
	<div class="space-y-4">
		<Card title="General information">
			<div class="grid grid-cols-2 gap-3 text-xs font-semibold text-slate-600">
				<label
					>Rule code<input
						class="mt-1 w-full rounded border-slate-300 font-mono text-sm"
						placeholder="VEHICLE_PRICE_BAND"
						bind:value={form.rule_code}
						required
					/></label
				>
				<label
					>Name<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.name}
						required
					/></label
				>
				<label
					>Category<select
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.category}
						>{#each meta?.rule_categories ?? [] as category (category.code)}<option
								value={category.code}>{category.label}</option
							>{/each}</select
					></label
				>
				<label
					>Rule kind<select
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.rule_kind}
						>{#each meta?.rule_kinds ?? ['POLICY_OUTCOME', 'STATEMENT', 'CLASSIFICATION'] as kind (kind)}{#if kind !== 'EXPRESSION' || auth.hasPermission('rule.author_expression')}<option
									value={kind}>{kind}</option
								>{/if}{/each}</select
					></label
				>
				<label
					>Version note<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.version_note}
					/></label
				>
				<label class="col-span-2"
					>Description<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.description}
					/></label
				>
			</div>
		</Card>

		<Card title="CASE WHEN branches">
			<BranchEditor {meta} {reasonCodes} bind:branches bind:defaultActions />
		</Card>
		{#if error}<ErrorNote {error} />{/if}
		<button
			class="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
			type="submit">Create draft rule</button
		>
	</div>

	<Card title="Live preview">
		<div class="mb-3 flex gap-2">
			<button
				class:font-bold={tab === 'human'}
				class="text-xs text-blue-700 underline"
				type="button"
				onclick={() => (tab = 'human')}>Human-readable</button
			>
			<button
				class:font-bold={tab === 'json'}
				class="text-xs text-blue-700 underline"
				type="button"
				onclick={() => (tab = 'json')}>Advanced JSON</button
			>
		</div>
		{#if tab === 'human'}
			<pre class="whitespace-pre-wrap rounded bg-slate-50 p-3 text-sm text-slate-700">{humanPreview(
					builderState
				)}</pre>
		{:else}
			<p class="mb-2 text-xs text-slate-500">Read-only generated definition.</p>
			<JsonBlock value={preview} />
		{/if}
	</Card>
</form>
