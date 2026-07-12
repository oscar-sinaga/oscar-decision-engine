<script lang="ts">
	import { Plus } from '@lucide/svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { RegisteredModel } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import DataTable, { type Column } from '$lib/ui/DataTable.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import { confirmAction } from '$lib/ui/confirm';
	import { toast } from 'svelte-sonner';

	type ModelRow = RegisteredModel &
		Record<string, unknown> & { status: string; actions: string; owner: string };
	let models = $state<RegisteredModel[] | null>(null);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let showCreate = $state(false);
	let loading = $state(true);
	let form = $state({
		code: '',
		version_label: '',
		name: '',
		provider: 'INTERNAL',
		description: ''
	});
	const canManage = $derived(auth.hasPermission('model.manage'));
	const rows = $derived(
		(models ?? []).map((model) => ({
			...model,
			status: model.active ? 'ACTIVE' : 'RETIRED',
			actions: '',
			owner: model.provider
		})) as ModelRow[]
	);
	async function load(): Promise<void> {
		error = null;
		loading = true;
		try {
			models = await api<RegisteredModel[]>('/v1/models');
		} catch (err) {
			error = err;
		} finally {
			loading = false;
		}
	}
	$effect(() => {
		load();
	});
	async function create(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		actionError = null;
		try {
			await api('/v1/models', { body: { ...form } });
			showCreate = false;
			form = { code: '', version_label: '', name: '', provider: 'INTERNAL', description: '' };
			await load();
			toast.success('Model version registered');
		} catch (err) {
			actionError = err;
			toast.error(err instanceof ApiError ? err.message : 'Could not register model version');
		}
	}
	async function toggle(model: RegisteredModel): Promise<void> {
		const confirmation = await confirmAction({
			title: model.active ? 'Retire model version?' : 'Reactivate model version?',
			body: `${model.code} ${model.version_label}`,
			confirmLabel: model.active ? 'Retire' : 'Reactivate',
			tone: model.active ? 'danger' : 'default',
			requireReason: true
		});
		if (!confirmation.ok) return;
		actionError = null;
		try {
			await api(`/v1/models/${model.id}`, { method: 'PATCH', body: { active: !model.active } });
			await load();
			toast.success(model.active ? 'Model version retired' : 'Model version reactivated');
		} catch (err) {
			actionError = err;
			toast.error(err instanceof ApiError ? err.message : 'Could not update model status');
		}
	}
</script>

{#snippet nameCell(row: ModelRow)}<div>
		<div class="font-mono text-xs font-medium">{row.code}</div>
		<div class="text-[11px] text-text-muted">{row.name}</div>
	</div>{/snippet}
{#snippet statusCell(row: ModelRow)}<StatusBadge value={row.status} />{/snippet}
{#snippet dateCell(row: ModelRow)}{#if row.created_at}<RelativeTime
			value={row.created_at}
		/>{:else}—{/if}{/snippet}
{#snippet actionsCell(row: ModelRow)}{#if canManage}<Button
			variant="ghost"
			size="xs"
			onclick={() => toggle(row)}>{row.active ? 'Retire' : 'Reactivate'}</Button
		>{/if}{/snippet}
{#if true}
	{@const columns: Column<ModelRow>[] = [
		{ key: 'code', header: 'Name', sortable: true, cell: nameCell },
		{ key: 'version_label', header: 'Version', sortable: true },
		{ key: 'status', header: 'Status', cell: statusCell },
		{ key: 'owner', header: 'Owner', sortable: true },
		{ key: 'created_at', header: 'Registered', sortable: true, cell: dateCell },
		{ key: 'actions', header: '', align: 'right', cell: actionsCell }
	]}
	{#snippet actions()}{#if canManage}<Button size="sm" onclick={() => (showCreate = !showCreate)}
				><Plus size={15} /> Register model</Button
			>{/if}{/snippet}
	<PageHeader
		title="Model Registry"
		description="Scoring-model versions referenced by governed scorecards."
		{actions}
	/>
	{#if showCreate}
		<Card.Root class="mb-4"
			><Card.Header><Card.Title>Register model version</Card.Title></Card.Header><Card.Content>
				<form class="grid gap-3 md:grid-cols-2" onsubmit={create}>
					<div class="space-y-1.5">
						<Label for="model-code">Code</Label><Input
							id="model-code"
							class="font-mono"
							placeholder="MOTOR_SCORE"
							bind:value={form.code}
							required
						/>
					</div>
					<div class="space-y-1.5">
						<Label for="model-version">Version label</Label><Input
							id="model-version"
							placeholder="V2"
							bind:value={form.version_label}
							required
						/>
					</div>
					<div class="space-y-1.5">
						<Label for="model-name">Name</Label><Input
							id="model-name"
							bind:value={form.name}
							required
						/>
					</div>
					<div class="space-y-1.5">
						<Label for="model-provider">Provider</Label><Input
							id="model-provider"
							bind:value={form.provider}
						/>
					</div>
					<div class="space-y-1.5 md:col-span-2">
						<Label for="model-description">Description</Label><Input
							id="model-description"
							bind:value={form.description}
						/>
					</div>
					<div class="md:col-span-2 flex gap-2">
						<Button type="submit">Register</Button><Button
							variant="outline"
							onclick={() => (showCreate = false)}>Cancel</Button
						>
					</div>
				</form>
				{#if actionError}<div class="mt-3"><ErrorNote error={actionError} /></div>{/if}
			</Card.Content></Card.Root
		>
	{/if}
	{#if error}<ErrorNote {error} />{:else}<DataTable
			{columns}
			{rows}
			{loading}
			rowKey="id"
			testId="models-table"
			empty={{
				title: 'No models registered',
				hint: 'Register a model version to document scorecard dependencies.'
			}}
		/>{/if}
{/if}
