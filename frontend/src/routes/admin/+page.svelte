<script lang="ts">
	import { Check, ExternalLink, ShieldCheck, UserCog } from '@lucide/svelte';
	import { api, ApiError } from '$lib/api/client';
	import type {
		AdminUser,
		ApprovalRequest,
		ConfigEntity,
		RoleMatrixItem,
		Rule,
		Strategy
	} from '$lib/api/types';
	import * as Dialog from '$lib/components/ui/dialog';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import { confirmAction } from '$lib/ui/confirm';
	import { toast } from 'svelte-sonner';

	type Tab = 'approvals' | 'users' | 'roles';
	type ApprovalTarget = { endpoint: string; label: string };

	let users = $state<AdminUser[]>([]);
	let roles = $state<RoleMatrixItem[]>([]);
	let approvals = $state<ApprovalRequest[]>([]);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let editingUser = $state<AdminUser | null>(null);
	let editingRoles = $state<string[]>([]);
	let activeTab = $state<Tab>('approvals');
	let busyApproval = $state<string | null>(null);

	const pendingApprovals = $derived(approvals.filter((approval) => approval.status === 'PENDING'));
	const permissions = $derived(
		Array.from(new Set(roles.flatMap((role) => role.permissions))).sort((a, b) =>
			a.localeCompare(b)
		)
	);

	async function load(): Promise<void> {
		error = null;
		try {
			[users, roles] = await Promise.all([
				api<AdminUser[]>('/v1/admin/users'),
				api<RoleMatrixItem[]>('/v1/admin/roles')
			]);
		} catch (err) {
			error = err;
		}
		try {
			approvals = await api<ApprovalRequest[]>('/v1/approvals');
		} catch {
			approvals = [];
		}
	}

	$effect(() => {
		load();
	});

	function startEdit(user: AdminUser): void {
		editingUser = user;
		editingRoles = [...user.roles];
	}

	function toggleRole(code: string): void {
		editingRoles = editingRoles.includes(code)
			? editingRoles.filter((role) => role !== code)
			: [...editingRoles, code];
	}

	async function saveRoles(): Promise<void> {
		if (!editingUser) return;
		const confirmation = await confirmAction({
			title: `Update roles for ${editingUser.username}?`,
			body: 'The user’s permissions will change immediately.',
			confirmLabel: 'Update roles',
			requireReason: true
		});
		if (!confirmation.ok) return;
		actionError = null;
		try {
			await api(`/v1/admin/users/${editingUser.username}/roles`, {
				method: 'PUT',
				body: { roles: editingRoles }
			});
			editingUser = null;
			toast.success('User roles updated');
			await load();
		} catch (err) {
			actionError = err;
			toast.error(err instanceof ApiError ? err.message : 'Could not update user roles');
		}
	}

	async function resolveApprovalTarget(approval: ApprovalRequest): Promise<ApprovalTarget> {
		const versionNumber = approval.entity_version ?? '';
		if (approval.entity_type === 'RULE_VERSION') {
			const entities = await api<Rule[]>('/v1/rules');
			const entity = entities.find((item) => item.rule_code === approval.entity_id);
			if (!entity) throw new Error(`Rule ${approval.entity_id} was not found`);
			const detail = await api<Rule>(`/v1/rules/${entity.id}`);
			const version = detail.versions?.find((item) => String(item.version) === versionNumber);
			if (!version) throw new Error(`Rule version ${versionNumber} was not found`);
			return {
				endpoint: `/v1/rules/${entity.id}/versions/${version.id}`,
				label: entity.rule_code
			};
		}
		if (approval.entity_type === 'STRATEGY_VERSION') {
			const entities = await api<Strategy[]>('/v1/strategies');
			const entity = entities.find((item) => item.strategy_code === approval.entity_id);
			if (!entity) throw new Error(`Strategy ${approval.entity_id} was not found`);
			const detail = await api<Strategy>(`/v1/strategies/${entity.id}`);
			const version = detail.versions?.find((item) => String(item.version) === versionNumber);
			if (!version) throw new Error(`Strategy version ${versionNumber} was not found`);
			return {
				endpoint: `/v1/strategies/${entity.id}/versions/${version.id}`,
				label: entity.strategy_code
			};
		}
		const kind = approval.entity_type === 'SCORECARD_VERSION' ? 'scorecards' : 'decision-tables';
		if (!['SCORECARD_VERSION', 'DECISION_TABLE_VERSION'].includes(approval.entity_type)) {
			throw new Error(`Unsupported approval type ${approval.entity_type}`);
		}
		const entities = await api<ConfigEntity[]>(`/v1/${kind}`);
		const entity = entities.find((item) => item.code === approval.entity_id);
		if (!entity) throw new Error(`${approval.entity_id} was not found`);
		const detail = await api<ConfigEntity>(`/v1/${kind}/${entity.id}`);
		const version = detail.versions.find((item) => String(item.version) === versionNumber);
		if (!version) throw new Error(`Version ${versionNumber} was not found`);
		return { endpoint: `/v1/${kind}/${entity.id}/versions/${version.id}`, label: entity.code };
	}

	async function decideApproval(
		approval: ApprovalRequest,
		action: 'activate' | 'reject'
	): Promise<void> {
		const isReject = action === 'reject';
		const confirmation = await confirmAction({
			title: isReject ? 'Reject approval request?' : 'Approve and activate this version?',
			body: `${approval.entity_type} ${approval.entity_id} v${approval.entity_version ?? '—'}`,
			confirmLabel: isReject ? 'Reject' : 'Approve & activate',
			tone: isReject ? 'danger' : 'default',
			requireReason: true
		});
		if (!confirmation.ok) return;
		busyApproval = approval.request_id;
		actionError = null;
		try {
			const target = await resolveApprovalTarget(approval);
			await api(`${target.endpoint}/${action}`, { body: { reason: confirmation.reason ?? '' } });
			toast.success(isReject ? `${target.label} rejected` : `${target.label} activated`);
			await load();
		} catch (err) {
			actionError = err;
			toast.error(
				err instanceof ApiError
					? err.message
					: isReject
						? 'Could not reject approval'
						: 'Could not approve request'
			);
		} finally {
			busyApproval = null;
		}
	}
</script>

<PageHeader title="Admin" description="Govern approvals, user access, and role permissions." />

<div
	class="mb-4 flex gap-1 rounded-control border border-border bg-surface p-1"
	role="tablist"
	aria-label="Admin sections"
>
	{#each [{ id: 'approvals', label: `Approvals (${pendingApprovals.length})` }, { id: 'users', label: 'Users' }, { id: 'roles', label: 'Roles' }] as tab (tab.id)}
		<button
			type="button"
			role="tab"
			aria-selected={activeTab === tab.id}
			class="rounded-control px-3 py-2 text-xs font-semibold {activeTab === tab.id
				? 'bg-primary-50 text-primary-700'
				: 'text-text-muted hover:bg-surface-muted'}"
			onclick={() => (activeTab = tab.id as Tab)}
		>
			{tab.label}
		</button>
	{/each}
</div>

{#if error}<ErrorNote {error} />{:else}
	{#if actionError}<div class="mb-4"><ErrorNote error={actionError} /></div>{/if}

	{#if activeTab === 'approvals'}
		<div class="grid gap-3 xl:grid-cols-2">
			{#each pendingApprovals as approval (approval.request_id)}
				<article class="rounded-card border border-border bg-surface p-4 shadow-card">
					<div class="flex items-start justify-between gap-3">
						<div class="flex min-w-0 gap-3">
							<span
								class="flex size-9 shrink-0 items-center justify-center rounded-control bg-primary-50 text-primary-700"
								><ShieldCheck size={18} /></span
							>
							<div class="min-w-0">
								<p class="font-mono text-xs font-semibold text-text">
									{approval.entity_id} · v{approval.entity_version ?? '—'}
								</p>
								<p class="mt-0.5 text-[11px] text-text-muted">
									{approval.entity_type.replaceAll('_', ' ')} · requested by {approval.requested_by ??
										'unknown'} · <RelativeTime value={approval.created_at} />
								</p>
							</div>
						</div>
						<StatusBadge value={approval.status} />
					</div>
					<div class="mt-3 rounded-control bg-surface-muted p-3 text-xs text-text-muted">
						<p>{approval.change_summary || 'No change summary.'}</p>
						{#if approval.request_reason}<p class="mt-2">
								<strong class="text-text">Request reason:</strong>
								{approval.request_reason}
							</p>{/if}
					</div>
					{#if approval.simulation_ref}<a
							class="mt-3 inline-flex items-center gap-1 font-mono text-[11px] text-primary-700 hover:underline"
							href="/simulations">Simulation {approval.simulation_ref}<ExternalLink size={12} /></a
						>{/if}
					<div class="mt-4 flex justify-end gap-2">
						<button
							class="rounded-control border border-danger/25 bg-surface px-3 py-2 text-xs font-semibold text-danger hover:bg-danger-bg disabled:opacity-50"
							disabled={busyApproval === approval.request_id}
							onclick={() => decideApproval(approval, 'reject')}>Reject</button
						><button
							class="rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
							disabled={busyApproval === approval.request_id}
							onclick={() => decideApproval(approval, 'activate')}>Approve</button
						>
					</div>
				</article>
			{:else}
				<div
					class="col-span-full rounded-card border border-border bg-surface p-10 text-center shadow-card"
				>
					<ShieldCheck class="mx-auto text-success" size={28} />
					<h2 class="mt-3 text-sm font-semibold text-text">Approval inbox is clear</h2>
					<p class="mt-1 text-xs text-text-muted">There are no pending maker-checker requests.</p>
				</div>
			{/each}
		</div>
	{:else if activeTab === 'users'}
		<div class="overflow-hidden rounded-card border border-border bg-surface shadow-card">
			<table class="w-full text-sm" data-testid="users-table">
				<thead class="bg-surface-sunken text-left text-xs text-text-muted"
					><tr
						><th scope="col" class="px-4 py-3">User</th><th scope="col" class="px-4 py-3"
							>Actor type</th
						><th scope="col" class="px-4 py-3">Roles</th><th
							scope="col"
							class="px-4 py-3 text-right">Action</th
						></tr
					></thead
				>
				<tbody class="divide-y divide-border"
					>{#each users as user (user.username)}<tr class="hover:bg-surface-muted"
							><td class="px-4 py-3"
								><p class="font-mono text-xs font-semibold text-text">{user.username}</p>
								<p class="text-xs text-text-muted">{user.full_name}</p></td
							><td class="px-4 py-3 text-xs text-text-muted">{user.actor_type}</td><td
								class="px-4 py-3"
								><div class="flex flex-wrap gap-1">
									{#each user.roles as role (role)}<span
											class="rounded-control bg-special-bg px-2 py-0.5 text-[10px] font-semibold text-special"
											>{role}</span
										>{:else}<span class="text-xs text-text-faint">No roles</span>{/each}
								</div></td
							><td class="px-4 py-3 text-right"
								><button
									class="inline-flex items-center gap-1 text-xs font-semibold text-primary-700 hover:underline"
									onclick={() => startEdit(user)}><UserCog size={14} />Edit roles</button
								></td
							></tr
						>{/each}</tbody
				>
			</table>
		</div>
	{:else}
		<div class="overflow-auto rounded-card border border-border bg-surface shadow-card">
			<table class="min-w-max w-full text-xs">
				<thead class="sticky top-0 bg-surface-sunken text-text-muted"
					><tr
						><th scope="col" class="sticky left-0 bg-surface-sunken px-4 py-3 text-left"
							>Permission</th
						>{#each roles as role (role.code)}<th scope="col" class="px-4 py-3 text-center"
								><span class="font-mono">{role.code}</span><span
									class="block text-[10px] font-normal">{role.name}</span
								></th
							>{/each}</tr
					></thead
				><tbody class="divide-y divide-border"
					>{#each permissions as permission (permission)}<tr
							><th
								scope="row"
								class="sticky left-0 bg-surface px-4 py-2 text-left font-mono font-medium text-text"
								>{permission}</th
							>{#each roles as role (role.code)}<td class="px-4 py-2 text-center"
									>{#if role.permissions.includes(permission)}<Check
											class="mx-auto text-success"
											size={15}
										/><span class="sr-only">Granted</span>{:else}<span class="text-text-faint"
											>—</span
										>{/if}</td
								>{/each}</tr
						>{/each}</tbody
				>
			</table>
		</div>
	{/if}
{/if}

<Dialog.Root
	open={editingUser !== null}
	onOpenChange={(open) => {
		if (!open) editingUser = null;
	}}
>
	{#if editingUser}<Dialog.Content class="sm:max-w-lg"
			><Dialog.Header
				><Dialog.Title>Edit roles</Dialog.Title><Dialog.Description
					>{editingUser.full_name} · {editingUser.username}</Dialog.Description
				></Dialog.Header
			>
			<div class="grid gap-2 py-2 sm:grid-cols-2">
				{#each roles as role (role.code)}<label
						class="flex items-start gap-2 rounded-control border border-border p-3"
						><input
							class="mt-0.5"
							type="checkbox"
							checked={editingRoles.includes(role.code)}
							onchange={() => toggleRole(role.code)}
						/><span
							><span class="block font-mono text-xs font-semibold text-text">{role.code}</span><span
								class="text-[11px] text-text-muted">{role.name}</span
							></span
						></label
					>{/each}
			</div>
			<Dialog.Footer
				><button
					class="rounded-control border border-border px-3 py-2 text-xs font-semibold text-text"
					onclick={() => (editingUser = null)}>Cancel</button
				><button
					class="rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white"
					onclick={saveRoles}>Save roles</button
				></Dialog.Footer
			></Dialog.Content
		>{/if}
</Dialog.Root>
