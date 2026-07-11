<script lang="ts">
	import { page } from '$app/state';
	import { SvelteSet } from 'svelte/reactivity';
	import { api } from '$lib/api/client';
	import type { Meta, ReasonCode, Rule, RuleUsage, RuleVersion } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import BranchEditor from '$lib/components/BranchEditor.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import {
		builderToJson,
		humanPreview,
		jsonToBuilder,
		type BuilderCondition,
		type BuilderState
	} from '$lib/rule-format';

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
	let tab = $state<'human' | 'json'>('human');
	let testValues = $state<Record<string, unknown>>({});
	let testResult = $state<Record<string, unknown> | null>(null);

	function definition(version: RuleVersion) {
		return version.condition && version.action
			? { rule_kind: version.rule_kind, condition: version.condition, action: version.action }
			: { rule_kind: version.rule_kind, branches: version.branches, default: version.default };
	}

	function choose(version: RuleVersion) {
		selectedVersion = version;
		const parsed = jsonToBuilder(definition(version));
		builder = parsed.state;
		supported = parsed.supported;
		editing = false;
		testResult = null;
		testValues = {};
	}

	async function load() {
		error = null;
		try {
			const loaded = await api<Rule>(`/v1/rules/${page.params.id}`);
			rule = loaded;
			const versions = loaded.versions ?? [];
			choose(versions.find((version) => version.id === selectedVersion?.id) ?? versions.at(-1)!);
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
		if (!builder) return [];
		const paths = new SvelteSet<string>();
		builder.branches.forEach((branch) => referenced(branch.when, paths));
		return [...paths].map(
			(path) =>
				meta?.features.find((feature) => feature.path === path) ?? {
					path,
					label: path,
					data_type: 'STRING'
				}
		);
	});

	function setTestValue(path: string, type: string, raw: string) {
		testValues[path] = type === 'NUMBER' ? Number(raw) : type === 'BOOLEAN' ? raw === 'true' : raw;
		testValues = { ...testValues };
	}

	async function runTest() {
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

	async function lifecycle(path: string, reason = '') {
		if (!rule || !selectedVersion) return;
		try {
			await api(`/v1/rules/${rule.id}/versions/${selectedVersion.id}/${path}`, {
				body: { reason }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	function openEditor(newVersion: boolean) {
		if (!builder || !selectedVersion) return;
		builder = structuredClone(builder);
		builder.form = 'branched';
		editorNote = newVersion ? '' : selectedVersion.version_note;
		asNewVersion = newVersion;
		editing = true;
	}

	async function save() {
		if (!rule || !selectedVersion || !builder) return;
		try {
			const body = { ...builderToJson(builder), version_note: editorNote };
			await api(
				asNewVersion
					? `/v1/rules/${rule.id}/versions`
					: `/v1/rules/${rule.id}/versions/${selectedVersion.id}`,
				{
					method: asNewVersion ? 'POST' : 'PUT',
					body
				}
			);
			editing = false;
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	const canCreate = $derived(auth.hasPermission('rule.create'));
	const canApprove = $derived(auth.hasPermission('rule.approve'));
</script>

<a class="text-xs text-blue-700 underline" href="/rules">← Back to rules</a>
{#if error}<div class="mt-3"><ErrorNote {error} /></div>
{:else if rule && selectedVersion}
	<div class="mt-2 mb-4">
		<h1 class="text-xl font-bold text-slate-800">{rule.rule_code}</h1>
		<p class="text-sm text-slate-500">
			{rule.name} · {rule.category} · {selectedVersion.rule_kind}
		</p>
	</div>
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
		<Card title="Versions">
			<ul class="space-y-1">
				{#each rule.versions ?? [] as version (version.id)}<li>
						<button
							class="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm hover:bg-slate-50"
							class:bg-slate-100={selectedVersion.id === version.id}
							onclick={() => choose(version)}
							><span>v{version.version} <small>{version.version_note}</small></span><Badge
								value={version.status}
							/></button
						>
					</li>{/each}
			</ul>
			<div class="mt-3 flex flex-wrap gap-2 border-t pt-3">
				{#if canCreate && selectedVersion.status === 'DRAFT' && supported}<button
						class="rounded bg-slate-200 px-2 py-1 text-xs font-semibold"
						onclick={() => openEditor(false)}>Edit draft</button
					><button
						class="rounded bg-amber-500 px-2 py-1 text-xs font-semibold text-white"
						onclick={() => lifecycle('submit-approval')}>Submit</button
					>{/if}
				{#if canApprove && selectedVersion.status === 'PENDING_APPROVAL'}<button
						class="rounded bg-emerald-600 px-2 py-1 text-xs text-white"
						onclick={() => lifecycle('activate', 'Approved via workbench')}
						>Approve & activate</button
					><button
						class="rounded bg-red-600 px-2 py-1 text-xs text-white"
						onclick={() => lifecycle('reject', 'Rejected via workbench')}>Reject</button
					>{/if}
				{#if canApprove && selectedVersion.status === 'ACTIVE'}<button
						class="rounded bg-slate-600 px-2 py-1 text-xs text-white"
						onclick={() => lifecycle('retire', 'Retired via workbench')}>Retire</button
					>{/if}
				{#if canCreate && supported && ['ACTIVE', 'RETIRED', 'REJECTED'].includes(selectedVersion.status)}<button
						class="rounded bg-slate-200 px-2 py-1 text-xs"
						onclick={() => openEditor(true)}>New draft from this</button
					>{/if}
			</div>
		</Card>

		<Card title={`Definition v${selectedVersion.version}`}>
			{#if !supported}<p class="rounded bg-amber-50 p-2 text-xs text-amber-800">
					This stored shape exceeds builder capability. Preview is read-only.
				</p>{/if}
			<div class="my-2 flex gap-2">
				<button class="text-xs text-blue-700 underline" onclick={() => (tab = 'human')}
					>Human</button
				><button class="text-xs text-blue-700 underline" onclick={() => (tab = 'json')}
					>Advanced JSON</button
				>
			</div>
			{#if tab === 'human' && builder}<pre
					class="whitespace-pre-wrap rounded bg-slate-50 p-3 text-sm">{humanPreview(
						builder
					)}</pre>{:else}<JsonBlock value={definition(selectedVersion)} maxHeight="24rem" />{/if}
		</Card>

		<div class="space-y-4">
			<Card title="Test rule">
				<p class="mb-2 text-xs text-slate-500">Generated from referenced features.</p>
				<div class="space-y-2">
					{#each testFields as field (field.path)}<label
							class="block text-xs font-semibold text-slate-600"
							>{field.label}<input
								class="mt-1 w-full rounded border-slate-300 text-sm"
								type={field.data_type === 'NUMBER'
									? 'number'
									: field.data_type === 'DATE'
										? 'date'
										: 'text'}
								oninput={(event) =>
									setTestValue(field.path, field.data_type, event.currentTarget.value)}
							/></label
						>{/each}
				</div>
				<button class="mt-2 rounded bg-slate-900 px-3 py-1.5 text-xs text-white" onclick={runTest}
					>Run test</button
				>
				{#if testResult}<div class="mt-3">
						<JsonBlock value={testResult} maxHeight="14rem" />
					</div>{/if}
			</Card>
			<Card title="Used by">
				<p class="text-xs font-semibold text-slate-500">Rule sets</p>
				<ul class="text-sm">
					{#each usage?.rule_sets ?? [] as item (item.id)}<li>{item.code} · {item.name}</li>{/each}
				</ul>
				<p class="mt-2 text-xs font-semibold text-slate-500">Strategies</p>
				<ul class="text-sm">
					{#each usage?.strategies ?? [] as item (item.id)}<li>
							{item.strategy_code} · v{item.versions_using.join(', v')}
							{item.active_version_uses ? '· ACTIVE' : ''}
						</li>{/each}
				</ul>
				{#if usage?.strategies.some((item) => item.active_version_uses)}<p
						class="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-800"
					>
						Warning: this rule is used by an active strategy.
					</p>{/if}
			</Card>
		</div>
	</div>

	{#if editing && builder}<div class="mt-4">
			<Card title={asNewVersion ? 'New draft version' : 'Edit draft'}
				><BranchEditor
					{meta}
					{reasonCodes}
					bind:branches={builder.branches}
					bind:defaultActions={builder.defaultActions}
				/><label class="mt-3 block text-xs font-semibold"
					>Version note<input
						class="mt-1 w-full rounded border-slate-300"
						bind:value={editorNote}
					/></label
				>
				<div class="mt-3 flex gap-2">
					<button class="rounded bg-slate-900 px-3 py-1.5 text-xs text-white" onclick={save}
						>Save</button
					><button
						class="rounded bg-slate-200 px-3 py-1.5 text-xs"
						onclick={() => (editing = false)}>Cancel</button
					>
				</div></Card
			>
		</div>{/if}
	{#if actionError}<div class="mt-3"><ErrorNote error={actionError} /></div>{/if}
{:else}<p class="mt-3 text-sm text-slate-500">Loading…</p>{/if}
