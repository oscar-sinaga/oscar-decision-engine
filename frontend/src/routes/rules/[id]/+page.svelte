<script lang="ts">
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { Rule, RuleVersion } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';

	let rule = $state<Rule | null>(null);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let selectedVersion = $state<RuleVersion | null>(null);
	let testFeatures = $state('{\n  "affordability.dti": 0.5\n}');
	let testResult = $state<Record<string, unknown> | null>(null);
	let editorOpen = $state(false);
	let editorCondition = $state('');
	let editorAction = $state('');
	let editorNote = $state('');

	async function load() {
		error = null;
		try {
			rule = await api<Rule>(`/v1/rules/${page.params.id}`);
			const versions = rule.versions ?? [];
			selectedVersion =
				versions.find((v) => v.version === selectedVersion?.version) ??
				versions[versions.length - 1] ??
				null;
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
	});

	async function lifecycle(actionPath: string, reason = '') {
		if (!rule || !selectedVersion) return;
		actionError = null;
		try {
			await api(`/v1/rules/${rule.id}/versions/${selectedVersion.id}/${actionPath}`, {
				body: { reason }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	async function runTest() {
		if (!rule || !selectedVersion) return;
		actionError = null;
		testResult = null;
		try {
			testResult = await api(`/v1/rules/${rule.id}/versions/${selectedVersion.id}/test`, {
				body: { features: JSON.parse(testFeatures) }
			});
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Invalid JSON feature map');
		}
	}

	function openEditor(createNew: boolean) {
		if (!selectedVersion) return;
		editorOpen = true;
		editorCondition = JSON.stringify(selectedVersion.condition, null, 2);
		editorAction = JSON.stringify(selectedVersion.action, null, 2);
		editorNote = createNew ? '' : selectedVersion.version_note;
	}

	async function saveEditor(asNewVersion: boolean) {
		if (!rule || !selectedVersion) return;
		actionError = null;
		try {
			const body = {
				condition: JSON.parse(editorCondition),
				action: JSON.parse(editorAction),
				version_note: editorNote
			};
			if (asNewVersion) {
				await api(`/v1/rules/${rule.id}/versions`, { body });
			} else {
				await api(`/v1/rules/${rule.id}/versions/${selectedVersion.id}`, {
					method: 'PUT',
					body
				});
			}
			editorOpen = false;
			await load();
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Invalid JSON in editor');
		}
	}

	const canCreate = $derived(auth.hasPermission('rule.create'));
	const canApprove = $derived(auth.hasPermission('rule.approve'));
</script>

<a class="text-xs text-blue-700 underline" href="/rules">← Back to rules</a>

{#if error}
	<div class="mt-3"><ErrorNote {error} /></div>
{:else if rule}
	<div class="mt-2 mb-4">
		<h1 class="text-xl font-bold text-slate-800">{rule.rule_code}</h1>
		<p class="text-sm text-slate-500">{rule.name} · {rule.category} · owned by {rule.owner_team}</p>
	</div>

	<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
		<Card title="Versions">
			<ul class="space-y-1">
				{#each rule.versions ?? [] as version (version.id)}
					<li>
						<button
							class="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm {selectedVersion?.id ===
							version.id
								? 'bg-slate-100 font-semibold'
								: 'hover:bg-slate-50'}"
							onclick={() => (selectedVersion = version)}
						>
							<span
								>v{version.version}
								<span class="text-xs text-slate-400">{version.version_note}</span></span
							>
							<Badge value={version.status} />
						</button>
					</li>
				{/each}
			</ul>

			{#if selectedVersion}
				<div class="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
					{#if canCreate && selectedVersion.status === 'DRAFT'}
						<button
							class="rounded bg-slate-200 px-2 py-1 text-xs font-semibold"
							onclick={() => openEditor(false)}>Edit draft</button
						>
						<button
							class="rounded bg-amber-500 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('submit-approval')}>Submit for approval</button
						>
					{/if}
					{#if canApprove && selectedVersion.status === 'PENDING_APPROVAL'}
						<button
							class="rounded bg-emerald-600 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('activate', 'Approved via workbench')}
							>Approve &amp; activate</button
						>
						<button
							class="rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('reject', 'Rejected via workbench')}>Reject</button
						>
					{/if}
					{#if canApprove && selectedVersion.status === 'ACTIVE'}
						<button
							class="rounded bg-slate-600 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('retire', 'Retired via workbench')}>Retire</button
						>
					{/if}
					{#if canCreate && ['ACTIVE', 'RETIRED', 'REJECTED'].includes(selectedVersion.status)}
						<button
							class="rounded bg-slate-200 px-2 py-1 text-xs font-semibold"
							onclick={() => openEditor(true)}>New draft from this</button
						>
					{/if}
				</div>
			{/if}
			{#if actionError}
				<div class="mt-3"><ErrorNote error={actionError} /></div>
			{/if}
		</Card>

		<Card title={selectedVersion ? `Definition v${selectedVersion.version}` : 'Definition'}>
			{#if selectedVersion}
				<h3 class="mb-1 text-xs font-semibold text-slate-500 uppercase">Condition</h3>
				<JsonBlock value={selectedVersion.condition} maxHeight="14rem" />
				<h3 class="mt-3 mb-1 text-xs font-semibold text-slate-500 uppercase">Action</h3>
				<JsonBlock value={selectedVersion.action} maxHeight="8rem" />
			{/if}
		</Card>

		<Card title="Test rule (dry run)">
			<p class="mb-2 text-xs text-slate-500">Flat feature map used for evaluation:</p>
			<textarea
				class="h-32 w-full rounded border-slate-300 font-mono text-xs"
				bind:value={testFeatures}></textarea>
			<button
				class="mt-2 rounded bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
				onclick={runTest}>Run test</button
			>
			{#if testResult}
				<div class="mt-3"><JsonBlock value={testResult} maxHeight="16rem" /></div>
			{/if}
		</Card>
	</div>

	{#if editorOpen}
		<div class="mt-4">
			<Card title="Edit definition (JSON)">
				<div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
					<label class="text-xs font-semibold text-slate-600">
						Condition
						<textarea
							class="mt-1 h-48 w-full rounded border-slate-300 font-mono text-xs"
							bind:value={editorCondition}></textarea>
					</label>
					<label class="text-xs font-semibold text-slate-600">
						Action
						<textarea
							class="mt-1 h-48 w-full rounded border-slate-300 font-mono text-xs"
							bind:value={editorAction}></textarea>
					</label>
				</div>
				<label class="mt-2 block text-xs font-semibold text-slate-600">
					Version note
					<input class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={editorNote} />
				</label>
				<div class="mt-3 flex gap-2">
					{#if selectedVersion?.status === 'DRAFT'}
						<button
							class="rounded bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => saveEditor(false)}>Save draft</button
						>
					{/if}
					<button
						class="rounded bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white"
						onclick={() => saveEditor(true)}>Save as new version</button
					>
					<button
						class="rounded bg-slate-200 px-3 py-1.5 text-xs font-semibold"
						onclick={() => (editorOpen = false)}>Cancel</button
					>
				</div>
			</Card>
		</div>
	{/if}
{:else}
	<p class="mt-3 text-sm text-slate-500">Loading…</p>
{/if}
