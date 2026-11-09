<script lang="ts">
	import { appPath } from '$lib/app-path';

	import { goto } from '$app/navigation';
	import { ArrowLeft, Save } from '@lucide/svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { Meta, ReasonCode, Rule } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import BranchEditor from '$lib/components/BranchEditor.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import ExpressionEditor from '$lib/components/ExpressionEditor.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import SqlPreview from '$lib/components/SqlPreview.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import * as Tabs from '$lib/components/ui/tabs';
	import {
		builderToJson,
		expressionSqlPreview,
		humanPreview,
		sqlPreview,
		type BuilderAction,
		type BuilderBranch,
		type BuilderState
	} from '$lib/rule-format';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import { toast } from 'svelte-sonner';

	let meta = $state<Meta | null>(null);
	let reasonCodes = $state<ReasonCode[]>([]);
	let error = $state<unknown>(null);
	let tab = $state('builder');
	let expression = $state('');
	let outputTarget = $state('');
	let saving = $state(false);
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
	let isExpression = $derived(form.rule_kind === 'EXPRESSION');
	let preview = $derived(
		isExpression
			? { rule_kind: 'EXPRESSION', expression, output_target: outputTarget }
			: builderToJson(builderState)
	);
	let liveSqlPreview = $derived(
		isExpression
			? expressionSqlPreview(expression, outputTarget || 'outputs.target')
			: sqlPreview(builderState)
	);

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

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		error = null;
		saving = true;
		try {
			const definition = isExpression
				? { expression, output_target: outputTarget }
				: builderToJson(builderState);
			const rule = await api<Rule>('/v1/rules', { body: { ...form, ...definition } });
			toast.success('Rule created');
			goto(appPath(`/rules/${rule.id}`));
		} catch (err) {
			error = err;
			toast.error(err instanceof ApiError ? err.message : 'Could not create rule');
		} finally {
			saving = false;
		}
	}
</script>

{#snippet actions()}<Button href={appPath(`/rules`)} variant="outline" size="sm"
		><ArrowLeft size={15} /> Back to rules</Button
	>{/snippet}
<PageHeader
	title="Create rule"
	description="Build a governed rule version with typed branches and outputs."
	{actions}
/>

<form class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]" onsubmit={submit}>
	<div class="min-w-0">
		<Tabs.Root bind:value={tab}>
			<Tabs.List variant="line" class="mb-3">
				<Tabs.Trigger value="builder">Builder</Tabs.Trigger>
				<Tabs.Trigger value="sql">SQL preview</Tabs.Trigger>
				<Tabs.Trigger value="json">Advanced JSON</Tabs.Trigger>
				<Tabs.Trigger value="preview">Human preview</Tabs.Trigger>
			</Tabs.List>
			<Tabs.Content value="builder">
				<Card.Root>
					<Card.Header
						><Card.Title>{isExpression ? 'Safe expression' : 'CASE WHEN branches'}</Card.Title
						><Card.Description
							>{isExpression
								? 'Admin-gated expression language; raw SQL is never executed.'
								: 'Rules evaluate branches top to bottom and apply the first matching branch.'}</Card.Description
						></Card.Header
					>
					<Card.Content
						>{#if isExpression}<ExpressionEditor
								{meta}
								bind:expression
								bind:outputTarget
							/>{:else}<BranchEditor
								{meta}
								{reasonCodes}
								bind:branches
								bind:defaultActions
							/>{/if}</Card.Content
					>
				</Card.Root>
			</Tabs.Content>
			<Tabs.Content value="sql"><SqlPreview value={liveSqlPreview} /></Tabs.Content>
			<Tabs.Content value="json"
				><p class="mb-2 text-xs text-text-muted">Read-only generated definition.</p>
				<JsonBlock value={preview} maxHeight="36rem" /></Tabs.Content
			>
			<Tabs.Content value="preview"
				><pre
					class="whitespace-pre-wrap rounded-card border border-border bg-surface p-4 text-sm text-text">{isExpression
						? `${expression || 'Expression'} → ${outputTarget || 'output target'}`
						: humanPreview(builderState)}</pre></Tabs.Content
			>
		</Tabs.Root>
		{#if error}<div class="mt-4"><ErrorNote {error} /></div>{/if}
	</div>

	<aside class="space-y-4 xl:sticky xl:top-20 xl:self-start">
		<Card.Root>
			<Card.Header
				><Card.Title>Rule metadata</Card.Title><Card.Description
					>Identity and ownership of the first draft.</Card.Description
				></Card.Header
			>
			<Card.Content class="space-y-3">
				<div class="space-y-1.5">
					<Label for="rule-code">Rule code</Label><Input
						id="rule-code"
						class="font-mono"
						placeholder="VEHICLE_PRICE_BAND"
						bind:value={form.rule_code}
						required
					/>
				</div>
				<div class="space-y-1.5">
					<Label for="rule-name">Name</Label><Input
						id="rule-name"
						bind:value={form.name}
						required
					/>
				</div>
				<div class="space-y-1.5">
					<Label for="rule-category">Category</Label><select
						id="rule-category"
						class="block h-9 w-full rounded-control border-border text-sm"
						bind:value={form.category}
						>{#each meta?.rule_categories ?? [] as category (category.code)}<option
								value={category.code}>{category.label}</option
							>{/each}</select
					>
				</div>
				<div class="space-y-1.5">
					<Label for="rule-kind">Rule kind</Label><select
						id="rule-kind"
						class="block h-9 w-full rounded-control border-border text-sm"
						bind:value={form.rule_kind}
						>{#each meta?.rule_kinds ?? ['POLICY_OUTCOME', 'STATEMENT', 'CLASSIFICATION'] as kind (kind)}{#if kind !== 'EXPRESSION' || auth.hasPermission('rule.author_expression')}<option
									value={kind}>{kind}</option
								>{/if}{/each}</select
					>
				</div>
				<div class="space-y-1.5">
					<Label for="rule-description">Description</Label><Input
						id="rule-description"
						bind:value={form.description}
					/>
				</div>
				<div class="space-y-1.5">
					<Label for="rule-note">Version note</Label><Input
						id="rule-note"
						bind:value={form.version_note}
					/>
				</div>
			</Card.Content>
			<Card.Footer
				><Button class="w-full" type="submit" disabled={saving}
					><Save size={15} /> {saving ? 'Creating…' : 'Create draft rule'}</Button
				></Card.Footer
			>
		</Card.Root>
		<Card.Root size="sm"
			><Card.Header><Card.Title>Authoring guidance</Card.Title></Card.Header><Card.Content
				class="space-y-2 text-xs text-text-muted"
				><p>
					Use <strong class="text-text">SET_OUTPUT</strong> for intermediate classifications consumed
					later by tables or strategy conditions.
				</p>
				<p>
					Keep the final decision in a decision table when multiple risk dimensions must be
					combined.
				</p></Card.Content
			></Card.Root
		>
	</aside>
</form>
