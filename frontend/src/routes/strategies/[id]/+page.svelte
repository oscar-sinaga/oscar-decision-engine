<script lang="ts">
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { Strategy, StrategyVersion } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';

	let strategy = $state<Strategy | null>(null);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let selected = $state<StrategyVersion | null>(null);
	let editorOpen = $state(false);
	let editorSteps = $state('');
	let editorNote = $state('');
	let rollbackReason = $state('');

	async function load() {
		error = null;
		try {
			strategy = await api<Strategy>(`/v1/strategies/${page.params.id}`);
			const versions = strategy.versions ?? [];
			selected =
				versions.find((v) => v.version === selected?.version) ??
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
		if (!strategy || !selected) return;
		actionError = null;
		try {
			await api(`/v1/strategies/${strategy.id}/versions/${selected.id}/${actionPath}`, {
				body: { reason }
			});
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	function openEditor() {
		if (!selected) return;
		editorSteps = JSON.stringify(
			selected.steps.map((s) => ({
				order: s.order,
				type: s.type,
				name: s.name,
				reference_code: s.reference_code,
				on_error: s.on_error,
				config: s.config
			})),
			null,
			2
		);
		editorNote = '';
		editorOpen = true;
	}

	async function saveEditor(asNewVersion: boolean) {
		if (!strategy || !selected) return;
		actionError = null;
		try {
			const body = { steps: JSON.parse(editorSteps), version_note: editorNote };
			if (asNewVersion) {
				await api(`/v1/strategies/${strategy.id}/versions`, { body });
			} else {
				await api(`/v1/strategies/${strategy.id}/versions/${selected.id}`, {
					method: 'PUT',
					body
				});
			}
			editorOpen = false;
			await load();
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Invalid JSON steps');
		}
	}

	const canCreate = $derived(auth.hasPermission('strategy.create'));
	const canActivate = $derived(auth.hasPermission('strategy.activate'));
</script>

<a class="text-xs text-blue-700 underline" href="/strategies">← Back to strategies</a>

{#if error}
	<div class="mt-3"><ErrorNote {error} /></div>
{:else if strategy}
	<div class="mt-2 mb-4">
		<h1 class="text-xl font-bold text-slate-800">{strategy.strategy_code}</h1>
		<p class="text-sm text-slate-500">
			{strategy.name} · {strategy.product_type} / {strategy.segment}
		</p>
	</div>

	<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
		<Card title="Versions">
			<ul class="space-y-1">
				{#each strategy.versions ?? [] as version (version.id)}
					<li>
						<button
							class="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm {selected?.id ===
							version.id
								? 'bg-slate-100 font-semibold'
								: 'hover:bg-slate-50'}"
							onclick={() => (selected = version)}
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

			{#if selected}
				<div class="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
					{#if canCreate && selected.status === 'DRAFT'}
						<button
							class="rounded bg-slate-200 px-2 py-1 text-xs font-semibold"
							onclick={openEditor}>Edit steps</button
						>
						<button
							class="rounded bg-amber-500 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('submit-approval')}>Submit for approval</button
						>
					{/if}
					{#if canActivate && selected.status === 'PENDING_APPROVAL'}
						<button
							class="rounded bg-emerald-600 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('activate', 'Activated via workbench')}
							>Approve &amp; activate</button
						>
						<button
							class="rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('reject', 'Rejected via workbench')}>Reject</button
						>
					{/if}
					{#if canCreate && ['ACTIVE', 'RETIRED', 'REJECTED'].includes(selected.status)}
						<button
							class="rounded bg-slate-200 px-2 py-1 text-xs font-semibold"
							onclick={openEditor}>New draft from this</button
						>
					{/if}
				</div>
				{#if canActivate && selected.status === 'RETIRED'}
					<div class="mt-3 border-t border-slate-100 pt-3">
						<label class="block text-xs font-semibold text-slate-600">
							Rollback reason (required)
							<input
								class="mt-1 w-full rounded border-slate-300 text-sm"
								bind:value={rollbackReason}
							/>
						</label>
						<button
							class="mt-2 rounded bg-purple-700 px-2 py-1 text-xs font-semibold text-white"
							onclick={() => lifecycle('rollback', rollbackReason)}>Rollback to this version</button
						>
					</div>
				{/if}
			{/if}
			{#if actionError}
				<div class="mt-3"><ErrorNote error={actionError} /></div>
			{/if}
		</Card>

		<div class="xl:col-span-2">
			<Card title={selected ? `Ordered steps — v${selected.version}` : 'Ordered steps'}>
				{#if selected}
					<ol class="space-y-2" data-testid="strategy-steps">
						{#each selected.steps as step (step.order)}
							<li class="rounded border border-slate-200 px-3 py-2">
								<div class="flex items-center justify-between text-sm">
									<span>
										<span class="mr-2 font-mono text-xs text-slate-400">#{step.order}</span>
										<span class="font-medium text-slate-800">{step.name}</span>
									</span>
									<span class="text-xs text-slate-500">
										{step.type}{step.reference_code ? ` → ${step.reference_code}` : ''} · on error: {step.on_error}
									</span>
								</div>
								{#if Object.keys(step.config).length > 0}
									<div class="mt-1 font-mono text-[11px] text-slate-500">
										{JSON.stringify(step.config)}
									</div>
								{/if}
							</li>
						{/each}
					</ol>
				{/if}
			</Card>

			{#if editorOpen}
				<div class="mt-4">
					<Card title="Edit steps (JSON)">
						<textarea
							class="h-72 w-full rounded border-slate-300 font-mono text-xs"
							bind:value={editorSteps}></textarea>
						<label class="mt-2 block text-xs font-semibold text-slate-600">
							Version note
							<input class="mt-1 w-full rounded border-slate-300 text-sm" bind:value={editorNote} />
						</label>
						<div class="mt-3 flex gap-2">
							{#if selected?.status === 'DRAFT'}
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
		</div>
	</div>
{:else}
	<p class="mt-3 text-sm text-slate-500">Loading…</p>
{/if}
