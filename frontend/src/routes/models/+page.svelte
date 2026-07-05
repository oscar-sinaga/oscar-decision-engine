<script lang="ts">
	import { api } from '$lib/api/client';
	import type { RegisteredModel } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { formatDateTime } from '$lib/format';

	let models = $state<RegisteredModel[] | null>(null);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let showCreate = $state(false);
	let form = $state({
		code: '',
		version_label: '',
		name: '',
		provider: 'INTERNAL',
		description: ''
	});

	async function load() {
		error = null;
		try {
			models = await api<RegisteredModel[]>('/v1/models');
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
	});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		actionError = null;
		try {
			await api('/v1/models', { body: { ...form } });
			showCreate = false;
			form = { code: '', version_label: '', name: '', provider: 'INTERNAL', description: '' };
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	async function toggle(model: RegisteredModel) {
		actionError = null;
		try {
			await api(`/v1/models/${model.id}`, { method: 'PATCH', body: { active: !model.active } });
			await load();
		} catch (err) {
			actionError = err;
		}
	}

	const canManage = $derived(auth.hasPermission('model.manage'));
</script>

<div class="mb-4 flex items-center justify-between">
	<div>
		<h1 class="text-xl font-bold text-slate-800">Model Registry</h1>
		<p class="text-sm text-slate-500">
			Scoring-model versions consumed by scorecards (documentation and lifecycle only).
		</p>
	</div>
	{#if canManage}
		<button
			class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700"
			onclick={() => (showCreate = !showCreate)}
		>
			{showCreate ? 'Cancel' : 'Register model'}
		</button>
	{/if}
</div>

{#if showCreate}
	<div class="mb-4">
		<Card title="Register model version">
			<form class="grid grid-cols-2 gap-3 text-xs font-semibold text-slate-600" onsubmit={create}>
				<label
					>Code
					<input
						class="mt-1 w-full rounded border-slate-300 font-mono text-sm"
						placeholder="MOTOR_SCORE"
						bind:value={form.code}
						required
					/></label
				>
				<label
					>Version label
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						placeholder="V2"
						bind:value={form.version_label}
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
					>Provider
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.provider}
					/></label
				>
				<label class="col-span-2"
					>Description
					<input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={form.description}
					/></label
				>
				<div class="col-span-2">
					<button
						class="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
						type="submit">Register</button
					>
				</div>
			</form>
			{#if actionError}
				<div class="mt-3"><ErrorNote error={actionError} /></div>
			{/if}
		</Card>
	</div>
{/if}

{#if error}
	<ErrorNote {error} />
{:else if models}
	<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
		<table class="min-w-full text-sm" data-testid="models-table">
			<thead class="bg-slate-50 text-left text-xs text-slate-500 uppercase">
				<tr>
					<th class="px-3 py-2">Code</th>
					<th class="px-3 py-2">Version</th>
					<th class="px-3 py-2">Name</th>
					<th class="px-3 py-2">Provider</th>
					<th class="px-3 py-2">Active</th>
					<th class="px-3 py-2">Registered</th>
					{#if canManage}<th class="px-3 py-2"></th>{/if}
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each models as model (model.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-3 py-2 font-mono text-xs">{model.code}</td>
						<td class="px-3 py-2 text-xs">{model.version_label}</td>
						<td class="px-3 py-2">{model.name}</td>
						<td class="px-3 py-2 text-xs">{model.provider}</td>
						<td class="px-3 py-2 text-xs">{model.active ? 'yes' : 'no'}</td>
						<td class="px-3 py-2 text-xs whitespace-nowrap">{formatDateTime(model.created_at)}</td>
						{#if canManage}
							<td class="px-3 py-2 text-right">
								<button class="text-xs text-blue-700 underline" onclick={() => toggle(model)}>
									{model.active ? 'Retire' : 'Reactivate'}
								</button>
							</td>
						{/if}
					</tr>
				{:else}
					<tr
						><td class="px-3 py-6 text-center text-slate-400" colspan="7">No models registered</td
						></tr
					>
				{/each}
			</tbody>
		</table>
	</div>
{:else}
	<p class="text-sm text-slate-500">Loading…</p>
{/if}
