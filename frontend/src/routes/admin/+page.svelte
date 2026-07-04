<script lang="ts">
	import { api } from '$lib/api/client';
	import type { AdminUser, ApprovalRequest, RoleMatrixItem } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { formatDateTime } from '$lib/format';

	let users = $state<AdminUser[]>([]);
	let roles = $state<RoleMatrixItem[]>([]);
	let approvals = $state<ApprovalRequest[]>([]);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let editingUser = $state<string | null>(null);
	let editingRoles = $state<string[]>([]);

	async function load() {
		error = null;
		try {
			users = await api<AdminUser[]>('/v1/admin/users');
			roles = await api<RoleMatrixItem[]>('/v1/admin/roles');
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

	function startEdit(user: AdminUser) {
		editingUser = user.username;
		editingRoles = [...user.roles];
	}

	function toggleRole(code: string) {
		editingRoles = editingRoles.includes(code)
			? editingRoles.filter((r) => r !== code)
			: [...editingRoles, code];
	}

	async function saveRoles() {
		if (!editingUser) return;
		actionError = null;
		try {
			await api(`/v1/admin/users/${editingUser}/roles`, {
				method: 'PUT',
				body: { roles: editingRoles }
			});
			editingUser = null;
			await load();
		} catch (err) {
			actionError = err;
		}
	}
</script>

<h1 class="mb-4 text-xl font-bold text-slate-800">Admin &amp; Governance</h1>

{#if error}
	<ErrorNote {error} />
{:else}
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
		<Card title="Users">
			<table class="w-full text-sm" data-testid="users-table">
				<thead class="text-left text-xs text-slate-500 uppercase">
					<tr
						><th class="py-1">User</th><th class="py-1">Type</th><th class="py-1">Roles</th><th
							class="py-1"
						></th></tr
					>
				</thead>
				<tbody class="divide-y divide-slate-100 align-top">
					{#each users as user (user.username)}
						<tr>
							<td class="py-2">
								<span class="font-medium">{user.username}</span>
								<span class="block text-xs text-slate-400">{user.full_name}</span>
							</td>
							<td class="py-2 text-xs">{user.actor_type}</td>
							<td class="py-2">
								{#if editingUser === user.username}
									<div class="flex flex-wrap gap-1.5">
										{#each roles as role (role.code)}
											<label
												class="flex items-center gap-1 rounded border border-slate-200 px-1.5 py-0.5 text-[11px]"
											>
												<input
													type="checkbox"
													class="h-3 w-3 rounded border-slate-300"
													checked={editingRoles.includes(role.code)}
													onchange={() => toggleRole(role.code)}
												/>
												{role.code}
											</label>
										{/each}
									</div>
								{:else}
									<span class="text-xs">{user.roles.join(', ') || '—'}</span>
								{/if}
							</td>
							<td class="py-2 text-right">
								{#if editingUser === user.username}
									<button
										class="rounded bg-slate-900 px-2 py-1 text-[11px] font-semibold text-white"
										onclick={saveRoles}>Save</button
									>
									<button class="ml-1 text-[11px] underline" onclick={() => (editingUser = null)}
										>Cancel</button
									>
								{:else}
									<button class="text-xs text-blue-700 underline" onclick={() => startEdit(user)}
										>Edit roles</button
									>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			{#if actionError}
				<div class="mt-3"><ErrorNote error={actionError} /></div>
			{/if}
		</Card>

		<div class="space-y-4">
			<Card title="Pending approvals">
				{#if approvals.filter((a) => a.status === 'PENDING').length === 0}
					<p class="text-sm text-slate-500">No pending approval requests.</p>
				{:else}
					<ul class="space-y-2 text-sm">
						{#each approvals.filter((a) => a.status === 'PENDING') as approval (approval.request_id)}
							<li class="rounded border border-slate-200 px-3 py-2">
								<div class="flex items-center justify-between">
									<span class="font-mono text-xs"
										>{approval.entity_type} · {approval.entity_id} v{approval.entity_version}</span
									>
									<Badge value={approval.status} />
								</div>
								<p class="text-xs text-slate-500">
									requested by {approval.requested_by} · {formatDateTime(approval.created_at)}
								</p>
							</li>
						{/each}
					</ul>
				{/if}
			</Card>

			<Card title="Role permission matrix">
				<div class="max-h-96 space-y-3 overflow-auto">
					{#each roles as role (role.code)}
						<div>
							<h3 class="text-xs font-bold text-slate-700">{role.code}</h3>
							<p class="font-mono text-[11px] leading-relaxed text-slate-500">
								{role.permissions.join(' · ')}
							</p>
						</div>
					{/each}
				</div>
			</Card>
		</div>
	</div>
{/if}
