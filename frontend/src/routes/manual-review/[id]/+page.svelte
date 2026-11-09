<script lang="ts">
	import { appPath } from '$lib/app-path';

	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import type { CaseDetail, ReasonCode } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import RelativeTime from '$lib/ui/RelativeTime.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import { toast } from 'svelte-sonner';
	import { formatCurrency, formatDateTime } from '$lib/format';

	let detail = $state<CaseDetail | null>(null);
	let reasonCodes = $state<ReasonCode[]>([]);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);

	let form = $state({
		analyst_decision: 'APPROVE_WITH_CONDITION',
		approved_limit: '',
		approved_tenor_months: '',
		override_reason_code: '',
		override_reason: '',
		notes: ''
	});
	let escalateReason = $state('');
	let escalateTo = $state('');
	let documentMessage = $state('');
	let documentNames = $state('');
	let commentBody = $state('');

	async function load() {
		error = null;
		try {
			detail = await api<CaseDetail>(`/v1/manual-review/cases/${page.params.id}`);
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
		api<ReasonCode[]>('/v1/reason-codes')
			.then((rc) => (reasonCodes = rc))
			.catch(() => {});
	});

	async function act(path: string, body: Record<string, unknown>) {
		if (!detail) return;
		actionError = null;
		try {
			detail = await api<CaseDetail>(`/v1/manual-review/cases/${detail.case_id}/${path}`, { body });
			toast.success('Manual-review case updated');
		} catch (err) {
			actionError = err;
			toast.error(err instanceof ApiError ? err.message : 'Could not update manual-review case');
		}
	}

	function submitDecision(event: SubmitEvent) {
		event.preventDefault();
		const approving = ['APPROVE', 'APPROVE_WITH_CONDITION'].includes(form.analyst_decision);
		act('decision', {
			analyst_decision: form.analyst_decision,
			approved_limit: approving && form.approved_limit ? Number(form.approved_limit) : null,
			approved_tenor_months:
				approving && form.approved_tenor_months ? Number(form.approved_tenor_months) : null,
			override_reason_code: form.override_reason_code || null,
			override_reason: form.override_reason,
			notes: form.notes
		});
	}

	const isOpen = $derived(
		detail !== null &&
			!['APPROVED_BY_ANALYST', 'REJECTED_BY_ANALYST', 'CLOSED'].includes(detail.status)
	);
	const canDecide = $derived(auth.hasPermission('manual_review.decide'));
</script>

{#if error}
	<div class="mb-4"><ErrorNote {error} /></div>
{:else if detail}
	<PageHeader
		title={detail.case_id}
		description={`Application ${detail.application_id} · priority ${detail.priority}`}
	>
		{#snippet actions()}
			<div class="flex flex-wrap items-center gap-2">
				<StatusBadge value={detail?.status ?? 'UNKNOWN'} />
				{#if detail?.sla_breached}<span
						class="rounded-full bg-danger-bg px-2.5 py-1 text-xs font-semibold text-danger"
						>SLA breached</span
					>{:else if detail?.sla_due_at}<span
						class="rounded-full bg-surface-sunken px-2.5 py-1 text-xs text-text-muted"
						>SLA <RelativeTime value={detail?.sla_due_at ?? ''} /></span
					>{/if}
				{#if detail?.escalated_to}<span
						class="rounded-full bg-special-bg px-2.5 py-1 text-xs text-special"
						>Escalated → {detail?.escalated_to}</span
					>{/if}
			</div>
		{/snippet}
	</PageHeader>

	{#if actionError}<div class="mb-4"><ErrorNote error={actionError} /></div>{/if}

	<div class="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
		<div class="space-y-4">
			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="text-sm font-semibold text-text">Application evidence</h2>
					<a
						class="font-mono text-xs text-primary-700 hover:underline"
						href={appPath(`/decisions/${detail.decision_id}`)}>View decision trace →</a
					>
				</div>
				<div class="grid gap-3 lg:grid-cols-3">
					<div>
						<h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
							Applicant (masked)
						</h3>
						<JsonBlock value={detail.applicant_summary} maxHeight="14rem" />
					</div>
					<div>
						<h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Loan</h3>
						<JsonBlock value={detail.loan_summary} maxHeight="14rem" />
					</div>
					<div>
						<h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
							Vehicle / collateral
						</h3>
						<JsonBlock value={detail.vehicle_summary} maxHeight="14rem" />
					</div>
				</div>
			</section>

			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<h2 class="text-sm font-semibold text-text">System decision</h2>
				<div class="mt-3 grid gap-4 md:grid-cols-[auto_1fr]">
					<div>
						<StatusBadge value={detail.system_decision} />
						<dl class="mt-3 space-y-1 text-xs">
							<div class="flex gap-6">
								<dt class="text-text-muted">Risk grade</dt>
								<dd class="font-semibold text-text">{detail.risk_grade ?? '—'}</dd>
							</div>
							<div class="flex gap-6">
								<dt class="text-text-muted">Score</dt>
								<dd class="font-semibold text-text">{detail.score ?? '—'}</dd>
							</div>
						</dl>
					</div>
					<div>
						<p class="text-xs font-semibold uppercase tracking-wide text-text-muted">
							Reason codes
						</p>
						<div class="mt-2 flex flex-wrap gap-2">
							{#each detail.system_reason_codes as code (code)}<span
									class="rounded-control bg-surface-sunken px-2 py-1 font-mono text-[11px] text-text"
									>{code}</span
								>{:else}<span class="text-xs text-text-muted">No reason codes.</span>{/each}
						</div>
					</div>
				</div>
			</section>

			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<h2 class="mb-3 text-sm font-semibold text-text">Document checklist</h2>
				<ul class="space-y-2" data-testid="document-checklist">
					{#each detail.documents as doc (doc.id)}<li
							class="flex items-center justify-between gap-3 rounded-control border border-border px-3 py-2"
						>
							<div class="min-w-0">
								<p class="truncate text-sm font-medium text-text">{doc.name}</p>
								<StatusBadge value={doc.status} />
							</div>
							{#if canDecide && doc.status === 'REQUESTED'}<div class="flex gap-2">
									<button
										class="text-xs font-semibold text-success hover:underline"
										onclick={() => act(`documents/${doc.id}/resolve`, { status: 'RECEIVED' })}
										>Mark received</button
									><button
										class="text-xs font-semibold text-text-muted hover:underline"
										onclick={() => act(`documents/${doc.id}/resolve`, { status: 'WAIVED' })}
										>Waive</button
									>
								</div>{/if}
						</li>{:else}<li class="rounded-control bg-surface-muted p-4 text-sm text-text-muted">
							No documents requested.
						</li>{/each}
				</ul>
			</section>

			{#if detail.notes}<section
					class="rounded-card border border-border bg-surface p-4 shadow-card"
				>
					<h2 class="mb-2 text-sm font-semibold text-text">Case notes</h2>
					<pre class="whitespace-pre-wrap text-xs text-text-muted">{detail.notes}</pre>
				</section>{/if}
		</div>

		<div class="space-y-4">
			{#if canDecide && isOpen}
				<section class="rounded-card border border-border bg-surface p-4 shadow-card">
					<div class="flex flex-wrap gap-2">
						<button
							class="rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted disabled:opacity-50"
							disabled={Boolean(detail.assigned_to)}
							onclick={() => act('assign', {})}
							>{detail.assigned_to ? `Assigned to ${detail.assigned_to}` : 'Assign to me'}</button
						>
					</div>
					<div class="mt-4 grid gap-3 sm:grid-cols-2">
						<label class="text-xs font-medium text-text-muted"
							>Escalate to<input
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								bind:value={escalateTo}
							/></label
						><label class="text-xs font-medium text-text-muted"
							>Escalation reason<input
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								bind:value={escalateReason}
							/></label
						>
					</div>
					<button
						class="mt-2 rounded-control bg-special px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
						disabled={!escalateReason.trim()}
						onclick={() =>
							act('escalate', { reason: escalateReason, escalated_to: escalateTo || null })}
						>Escalate</button
					>
					<div class="mt-4 border-t border-border pt-4">
						<label class="text-xs font-medium text-text-muted"
							>Document request message<input
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								bind:value={documentMessage}
							/></label
						><label class="mt-2 block text-xs font-medium text-text-muted"
							>Checklist items<input
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								placeholder="comma-separated"
								bind:value={documentNames}
							/></label
						><button
							class="mt-2 rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted"
							onclick={() =>
								act('request-documents', {
									message: documentMessage,
									document_names: documentNames
										? documentNames
												.split(',')
												.map((value) => value.trim())
												.filter(Boolean)
										: null
								})}>Request documents</button
						>
					</div>
				</section>

				<section class="rounded-card border border-primary-500/25 bg-surface p-4 shadow-card">
					<h2 class="text-sm font-semibold text-text">Analyst decision</h2>
					<p class="mt-1 text-xs text-text-muted">
						An override reason is required when your decision differs from the system
						recommendation.
					</p>
					<form
						class="mt-4 space-y-3"
						onsubmit={submitDecision}
						data-testid="analyst-decision-form"
					>
						<label class="block text-xs font-medium text-text-muted"
							>Decision<select
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								bind:value={form.analyst_decision}
								><option value="APPROVE">APPROVE</option><option value="APPROVE_WITH_CONDITION"
									>APPROVE WITH CONDITION</option
								><option value="REJECT">REJECT</option><option value="FRAUD_INVESTIGATION"
									>FRAUD INVESTIGATION</option
								></select
							></label
						>
						<div class="grid grid-cols-2 gap-3">
							<label class="text-xs font-medium text-text-muted"
								>Approved limit<input
									class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
									type="number"
									bind:value={form.approved_limit}
								/></label
							><label class="text-xs font-medium text-text-muted"
								>Tenor (months)<input
									class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
									type="number"
									bind:value={form.approved_tenor_months}
								/></label
							>
						</div>
						<label class="block text-xs font-medium text-text-muted"
							>Reason code<select
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								bind:value={form.override_reason_code}
								><option value="">— none —</option>{#each reasonCodes as rc (rc.code)}<option
										value={rc.code}>{rc.code}</option
									>{/each}</select
							></label
						>
						{#if form.analyst_decision !== detail.system_decision}<div
								class="rounded-control border border-warning/25 bg-warning-bg p-3 text-xs text-warning"
							>
								You are overriding the system decision. Explain the evidence and rationale below.
							</div>{/if}
						<label class="block text-xs font-medium text-text-muted"
							>Override reason<textarea
								class="mt-1 min-h-20 w-full rounded-control border border-border bg-surface p-2 text-sm text-text"
								bind:value={form.override_reason}></textarea></label
						>
						<label class="block text-xs font-medium text-text-muted"
							>Notes<textarea
								class="mt-1 min-h-20 w-full rounded-control border border-border bg-surface p-2 text-sm text-text"
								bind:value={form.notes}></textarea></label
						>
						<button
							class="w-full rounded-control bg-primary-600 py-2 text-sm font-semibold text-white hover:bg-primary-700"
							>Submit analyst decision</button
						>
					</form>
				</section>
			{:else if detail.analyst_decision}
				<section class="rounded-card border border-border bg-surface p-4 shadow-card">
					<h2 class="mb-3 text-sm font-semibold text-text">Final verdict</h2>
					<div class="grid grid-cols-2 gap-3">
						<div class="rounded-control bg-surface-muted p-3">
							<p class="mb-2 text-xs text-text-muted">System</p>
							<StatusBadge value={detail.system_decision} />
						</div>
						<div class="rounded-control bg-surface-muted p-3">
							<p class="mb-2 text-xs text-text-muted">Analyst</p>
							<StatusBadge value={detail.analyst_decision} />
						</div>
					</div>
					<dl class="mt-4 space-y-2 text-xs">
						<div class="flex justify-between">
							<dt class="text-text-muted">Decided by</dt>
							<dd>{detail.analyst_decided_by}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-text-muted">Decided at</dt>
							<dd>{formatDateTime(detail.analyst_decided_at)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-text-muted">Approved limit</dt>
							<dd>{formatCurrency(detail.approved_limit)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-text-muted">Approved tenor</dt>
							<dd>
								{detail.approved_tenor_months ? `${detail.approved_tenor_months} months` : '—'}
							</dd>
						</div>
					</dl>
					{#if detail.override_reason}<p
							class="mt-3 rounded-control bg-surface-muted p-3 text-xs text-text-muted"
						>
							{detail.override_reason}
						</p>{/if}
				</section>
			{/if}

			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<h2 class="mb-3 text-sm font-semibold text-text">Comments</h2>
				<ul class="mb-3 space-y-3" data-testid="comment-thread">
					{#each detail.comments as comment (comment.id)}<li
							class="rounded-control border border-border bg-surface-muted px-3 py-2"
						>
							<div class="flex justify-between text-[11px] text-text-faint">
								<span>{comment.author_label}</span><RelativeTime value={comment.created_at} />
							</div>
							<p class="mt-1 text-sm text-text">{comment.body}</p>
						</li>{:else}<li class="text-xs text-text-muted">No comments yet.</li>{/each}
				</ul>
				<textarea
					class="min-h-20 w-full rounded-control border border-border bg-surface p-2 text-sm text-text"
					placeholder="Add a comment…"
					bind:value={commentBody}></textarea><button
					class="mt-2 rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
					disabled={!commentBody.trim()}
					onclick={() => {
						act('comments', { body: commentBody });
						commentBody = '';
					}}>Add comment</button
				>
			</section>
		</div>
	</div>
{:else}
	<p class="mt-3 text-sm text-text-muted">Loading…</p>
{/if}
