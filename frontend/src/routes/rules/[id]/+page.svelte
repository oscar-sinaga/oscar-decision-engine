<script lang="ts">
	import { page } from '$app/state';
	import { ArrowLeft, Play, Save } from '@lucide/svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { api } from '$lib/api/client';
	import type { Meta, ReasonCode, Rule, RuleUsage, RuleVersion } from '$lib/api/types';
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
		humanPreview,
		jsonToBuilder,
		type BuilderCondition,
		type BuilderState
	} from '$lib/rule-format';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import VersionTimeline from '$lib/ui/VersionTimeline.svelte';
	import { setBreadcrumb } from '$lib/ui/breadcrumb.svelte';

	let rule = $state<Rule | null>(null);
	let meta = $state<Meta | null>(null);
	let reasonCodes = $state<ReasonCode[]>([]);
	let usage = $state<RuleUsage | null>(null);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let selectedVersion = $state<RuleVersion | null>(null);
	let builder = $state<BuilderState | null>(null);
	let supported = $state(false);
	let editing = $state(false);
	let asNewVersion = $state(false);
	let editorNote = $state('');
	let tab = $state('builder');
	let expressionDraft = $state('');
	let outputTargetDraft = $state('');
	let testValues = $state<Record<string, unknown>>({});
	let testResult = $state<Record<string, unknown> | null>(null);
	let saving = $state(false);

	function definition(version: RuleVersion): Record<string, unknown> {
		if (version.rule_kind === 'EXPRESSION') {
			return {
				rule_kind: version.rule_kind,
				expression: version.expression,
				output_target: version.output_target
			};
		}
		return version.condition && version.action
			? { rule_kind: version.rule_kind, condition: version.condition, action: version.action }
			: { rule_kind: version.rule_kind, branches: version.branches, default: version.default };
	}

	function choose(version: RuleVersion): void {
		selectedVersion = version;
		if (version.rule_kind === 'EXPRESSION') {
			builder = null;
			supported = true;
			expressionDraft = version.expression ?? '';
			outputTargetDraft = version.output_target ?? '';
		} else {
			const parsed = jsonToBuilder(definition(version));
			builder = parsed.state;
			supported = parsed.supported;
		}
		editing = false;
		testResult = null;
		testValues = {};
	}

	async function load(): Promise<void> {
		error = null;
		try {
			const loaded = await api<Rule>(`/v1/rules/${page.params.id}`);
			rule = loaded;
			setBreadcrumb(loaded.rule_code);
			const versions = loaded.versions ?? [];
			const next =
				versions.find((version) => version.id === selectedVersion?.id) ?? versions.at(-1);
			if (next) choose(next);
			usage = await api<RuleUsage>(`/v1/rules/${loaded.id}/usage`);
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
		api<Meta>('/v1/meta')
			.then((value) => (meta = value))
			.catch(() => {});
		api<ReasonCode[]>('/v1/reason-codes')
			.then((value) => (reasonCodes = value))
			.catch(() => {});
	});

	function referenced(
		condition: BuilderCondition,
		result = new SvelteSet<string>()
	): SvelteSet<string> {
		if (condition.kind === 'condition') result.add(condition.field);
		else condition.children.forEach((child) => referenced(child, result));
		return result;
	}

	let testFields = $derived.by(() => {
		const paths = new SvelteSet<string>();
		if (builder) builder.branches.forEach((branch) => referenced(branch.when, paths));
		else if (selectedVersion?.expression) {
			for (const token of selectedVersion.expression.match(/[A-Za-z_][A-Za-z0-9_.]*/g) ?? []) {
				if (meta?.features.some((feature) => feature.path === token)) paths.add(token);
			}
		}
		return [...paths].map(
			(path) =>
				meta?.features.find((feature) => feature.path === path) ?? {
					path,
					label: path,
					data_type: 'STRING'
				}
		);
	});

	function setTestValue(path: string, type: string, raw: string): void {
		testValues[path] = type === 'NUMBER' ? Number(raw) : type === 'BOOLEAN' ? raw === 'true' : raw;
		testValues = { ...testValues };
	}

	async function runTest(): Promise<void> {
		if (!rule || !selectedVersion) return;
		actionError = null;
		try {
			testResult = await api(`/v1/rules/${rule.id}/versions/${selectedVersion.id}/test`, {
				body: { features: testValues }
			});
		} catch (err) {
			actionError = err;
		}
	}

	async function lifecycle(path: string, reason = ''): Promise<void> {
		if (!rule || !selectedVersion) return;
		actionError = null;
		try {
			await api(`/v1/rules/${rule.id}/versions/${selectedVersion.id}/${path}`, {
				body: { reason }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	function openEditor(newVersion: boolean): void {
		if (!selectedVersion) return;
		if (selectedVersion.rule_kind === 'EXPRESSION') {
			expressionDraft = selectedVersion.expression ?? '';
			outputTargetDraft = selectedVersion.output_target ?? '';
		} else {
			if (!builder) return;
			builder = structuredClone($state.snapshot(builder));
			builder.form = 'branched';
		}
		editorNote = newVersion ? '' : selectedVersion.version_note;
		asNewVersion = newVersion;
		editing = true;
		tab = 'builder';
	}

	async function save(): Promise<void> {
		if (!rule || !selectedVersion) return;
		saving = true;
		actionError = null;
		try {
			const body =
				selectedVersion.rule_kind === 'EXPRESSION'
					? {
							rule_kind: 'EXPRESSION',
							expression: expressionDraft,
							output_target: outputTargetDraft,
							version_note: editorNote
						}
					: { ...builderToJson(builder!), version_note: editorNote };
			await api(
				asNewVersion
					? `/v1/rules/${rule.id}/versions`
					: `/v1/rules/${rule.id}/versions/${selectedVersion.id}`,
				{ method: asNewVersion ? 'POST' : 'PUT', body }
			);
			editing = false;
			await load();
		} catch (err) {
			actionError = err;
		} finally {
			saving = false;
		}
	}

	const canCreate = $derived(auth.hasPermission('rule.create'));
	const canApprove = $derived(auth.hasPermission('rule.approve'));
	const canAuthorExpression = $derived(auth.hasPermission('rule.author_expression'));
	const canEditSelected = $derived(
		canCreate && supported && (selectedVersion?.rule_kind !== 'EXPRESSION' || canAuthorExpression)
	);
</script>

{#snippet actions()}<Button href="/rules" variant="outline" size="sm"
		><ArrowLeft size={15} /> Back to rules</Button
	>{/snippet}
{#if error}
	<ErrorNote {error} />
{:else if rule && selectedVersion}
	<PageHeader
		title={rule.rule_code}
		description={`${rule.name} · ${rule.category} · ${selectedVersion.rule_kind}`}
		{actions}
	/>
	<div class="mb-4 flex items-center gap-2">
		<StatusBadge value={selectedVersion.status} /><span class="font-mono text-xs text-text-muted"
			>v{selectedVersion.version}</span
		>
	</div>

	<div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
		<div class="min-w-0">
			<Tabs.Root bind:value={tab}>
				<Tabs.List variant="line" class="mb-3">
					<Tabs.Trigger value="builder">Builder</Tabs.Trigger>
					<Tabs.Trigger value="sql">SQL preview</Tabs.Trigger>
					<Tabs.Trigger value="json">Advanced JSON</Tabs.Trigger>
					<Tabs.Trigger value="test">Test</Tabs.Trigger>
				</Tabs.List>
				<Tabs.Content value="builder">
					<Card.Root>
						<Card.Header
							><Card.Title
								>{editing
									? asNewVersion
										? 'New draft version'
										: 'Edit draft'
									: `Definition v${selectedVersion.version}`}</Card.Title
							><Card.Description
								>{editing
									? 'Edit the governed definition and save when validation is clean.'
									: 'Read-only human representation of the selected version.'}</Card.Description
							></Card.Header
						>
						<Card.Content>
							{#if !supported}<p
									class="mb-3 rounded-control bg-warning-bg p-2 text-xs text-warning"
								>
									This stored shape exceeds builder capability. Preview is read-only.
								</p>{/if}
							{#if editing}
								{#if selectedVersion.rule_kind === 'EXPRESSION'}<ExpressionEditor
										{meta}
										bind:expression={expressionDraft}
										bind:outputTarget={outputTargetDraft}
									/>{:else if builder}<BranchEditor
										{meta}
										{reasonCodes}
										bind:branches={builder.branches}
										bind:defaultActions={builder.defaultActions}
									/>{/if}
								<div class="mt-4 space-y-1.5">
									<Label for="editor-note">Version note</Label><Input
										id="editor-note"
										bind:value={editorNote}
									/>
								</div>
								<div class="mt-4 flex gap-2">
									<Button onclick={save} disabled={saving}
										><Save size={15} /> {saving ? 'Saving…' : 'Save'}</Button
									><Button variant="outline" onclick={() => (editing = false)}>Cancel</Button>
								</div>
							{:else}
								<pre
									class="whitespace-pre-wrap rounded-card bg-surface-muted p-4 text-sm text-text">{builder
										? humanPreview(builder)
										: `${selectedVersion.expression ?? ''} → ${selectedVersion.output_target ?? ''}`}</pre>
							{/if}
						</Card.Content>
					</Card.Root>
				</Tabs.Content>
				<Tabs.Content value="sql"><SqlPreview value={selectedVersion.sql_preview} /></Tabs.Content>
				<Tabs.Content value="json"
					><JsonBlock value={definition(selectedVersion)} maxHeight="38rem" /></Tabs.Content
				>
				<Tabs.Content value="test">
					<Card.Root
						><Card.Header
							><Card.Title>Test rule</Card.Title><Card.Description
								>Generated from every feature referenced by the selected definition.</Card.Description
							></Card.Header
						><Card.Content>
							<div class="grid gap-3 md:grid-cols-2">
								{#each testFields as field (field.path)}<div class="space-y-1.5">
										<Label for={`test-${field.path}`}>{field.label}</Label><Input
											id={`test-${field.path}`}
											type={field.data_type === 'NUMBER'
												? 'number'
												: field.data_type === 'DATE'
													? 'date'
													: 'text'}
											oninput={(event) =>
												setTestValue(field.path, field.data_type, event.currentTarget.value)}
										/>
									</div>{/each}
							</div>
							<Button class="mt-4" size="sm" onclick={runTest}><Play size={14} /> Run test</Button>
							{#if testResult}<div class="mt-4">
									<JsonBlock value={testResult} maxHeight="20rem" />
								</div>{/if}
						</Card.Content></Card.Root
					>
				</Tabs.Content>
			</Tabs.Root>
			{#if actionError}<div class="mt-4"><ErrorNote error={actionError} /></div>{/if}
		</div>

		<aside class="space-y-4 xl:sticky xl:top-20 xl:self-start">
			<Card.Root>
				<Card.Header><Card.Title>Versions</Card.Title></Card.Header>
				<Card.Content
					><VersionTimeline
						versions={(rule.versions ?? []).map((version) => ({
							id: version.id,
							version: version.version,
							status: version.status,
							note: version.version_note
						}))}
						selectedId={selectedVersion.id}
						onSelect={(id) => {
							const version = rule?.versions?.find((item) => item.id === id);
							if (version) choose(version);
						}}
					/></Card.Content
				>
			</Card.Root>

			<Card.Root>
				<Card.Header><Card.Title>Lifecycle</Card.Title></Card.Header>
				<Card.Content class="flex flex-wrap gap-2">
					{#if canEditSelected && selectedVersion.status === 'DRAFT'}<Button
							size="sm"
							variant="outline"
							onclick={() => openEditor(false)}>Edit draft</Button
						><Button size="sm" onclick={() => lifecycle('submit-approval')}>Submit</Button>{/if}
					{#if canApprove && selectedVersion.status === 'PENDING_APPROVAL'}<Button
							size="sm"
							onclick={() => lifecycle('activate', 'Approved via workbench')}
							>Approve & activate</Button
						><Button
							size="sm"
							variant="destructive"
							onclick={() => lifecycle('reject', 'Rejected via workbench')}>Reject</Button
						>{/if}
					{#if canApprove && selectedVersion.status === 'ACTIVE'}<Button
							size="sm"
							variant="destructive"
							onclick={() => lifecycle('retire', 'Retired via workbench')}>Retire</Button
						>{/if}
					{#if canEditSelected && ['ACTIVE', 'RETIRED', 'REJECTED'].includes(selectedVersion.status)}<Button
							size="sm"
							variant="outline"
							onclick={() => openEditor(true)}>New draft from this</Button
						>{/if}
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header><Card.Title>Used by</Card.Title></Card.Header>
				<Card.Content class="space-y-3 text-xs">
					<div>
						<p class="mb-1 font-semibold text-text-muted">Rule sets</p>
						<ul class="space-y-1">
							{#each usage?.rule_sets ?? [] as item (item.id)}<li>
									<span class="font-mono">{item.code}</span> · {item.name}
								</li>{/each}
						</ul>
					</div>
					<div>
						<p class="mb-1 font-semibold text-text-muted">Strategies</p>
						<ul class="space-y-1">
							{#each usage?.strategies ?? [] as item (item.id)}<li>
									<span class="font-mono">{item.strategy_code}</span> · v{item.versions_using.join(
										', v'
									)}
									{item.active_version_uses ? '· ACTIVE' : ''}
								</li>{/each}
						</ul>
					</div>
					{#if usage?.strategies.some((item) => item.active_version_uses)}<p
							class="rounded-control bg-warning-bg p-2 text-warning"
						>
							This rule is used by an active strategy.
						</p>{/if}
				</Card.Content>
			</Card.Root>
		</aside>
	</div>
{:else}
	<p class="text-sm text-text-muted">Loading rule…</p>
{/if}
