<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import type { CaseDetail, ReasonCode } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
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
	let documentMessage = $state('');

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
		} catch (err) {
			actionError = err;
		}
	}

	function submitDecision(event: SubmitEvent) {
		event.preventDefault();
		act('decision', {
			analyst_decision: form.analyst_decision,
			approved_limit: form.approved_limit ? Number(form.approved_limit) : null,
			approved_tenor_months: form.approved_tenor_months ? Number(form.approved_tenor_months) : null,
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

<a class="text-xs text-blue-700 underline" href="/manual-review">← Back to queue</a>

{#if error}
	<div class="mt-3"><ErrorNote {error} /></div>
{:else if detail}
	<div class="mt-2 mb-4 flex items-center gap-3">
		<h1 class="text-xl font-bold text-slate-800">{detail.case_id}</h1>
		<Badge value={detail.status} />
		<span class="text-xs text-slate-500">priority {detail.priority}</span>
	</div>

	<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
		<div class="space-y-4">
			<Card title="Decision by system">
				<div class="mb-2"><Badge value={detail.system_decision} kind="decision" /></div>
				<ul class="space-y-1 font-mono text-[11px] text-slate-600">
					{#each detail.system_reason_codes as code (code)}<li>{code}</li>{/each}
				</ul>
				<dl class="mt-3 space-y-1 text-sm">
					<div class="flex justify-between">
						<dt class="text-slate-500">Decision</dt>
						<dd>
							<a
								class="font-mono text-xs text-blue-700 underline"
								href="/decisions/{detail.decision_id}">{detail.decision_id}</a
							>
						</dd>
					</div>
					<div class="flex justify-between">
						<dt class="text-slate-500">Risk grade</dt>
						<dd>{detail.risk_grade ?? '—'}</dd>
					</div>
					<div class="flex justify-between">
						<dt class="text-slate-500">Score</dt>
						<dd>{detail.score ?? '—'}</dd>
					</div>
				</dl>
			</Card>

			<Card title="Decision by analyst">
				{#if detail.analyst_decision}
					<div class="mb-2"><Badge value={detail.analyst_decision} kind="decision" /></div>
					<dl class="space-y-1 text-sm">
						<div class="flex justify-between">
							<dt class="text-slate-500">Decided by</dt>
							<dd>{detail.analyst_decided_by}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-500">Decided at</dt>
							<dd>{formatDateTime(detail.analyst_decided_at)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-500">Approved limit</dt>
							<dd>{formatCurrency(detail.approved_limit)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-500">Approved tenor</dt>
							<dd>
								{detail.approved_tenor_months ? `${detail.approved_tenor_months} months` : '—'}
							</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-500">Reason code</dt>
							<dd class="font-mono text-xs">{detail.override_reason_code ?? '—'}</dd>
						</div>
					</dl>
					{#if detail.override_reason}
						<p class="mt-2 rounded bg-slate-50 p-2 text-xs text-slate-600">
							{detail.override_reason}
						</p>
					{/if}
				{:else}
					<p class="text-sm text-slate-500">No analyst decision yet.</p>
				{/if}
			</Card>
		</div>

		<div class="space-y-4">
			<Card title="Applicant summary (masked)">
				<JsonBlock value={detail.applicant_summary} maxHeight="12rem" />
			</Card>
			<Card title="Loan summary">
				<JsonBlock value={detail.loan_summary} maxHeight="8rem" />
			</Card>
			<Card title="Vehicle / collateral">
				<JsonBlock value={detail.vehicle_summary} maxHeight="10rem" />
			</Card>
			{#if detail.notes}
				<Card title="Notes">
					<pre class="text-xs whitespace-pre-wrap text-slate-600">{detail.notes}</pre>
				</Card>
			{/if}
		</div>

		<div class="space-y-4">
			{#if canDecide && isOpen}
				<Card title="Analyst decision">
					<form
						class="space-y-3 text-xs font-semibold text-slate-600"
						onsubmit={submitDecision}
						data-testid="analyst-decision-form"
					>
						<label class="block">
							Decision
							<select
								class="mt-1 w-full rounded border-slate-300 text-sm"
								bind:value={form.analyst_decision}
							>
								<option value="APPROVE">APPROVE</option>
								<option value="APPROVE_WITH_CONDITION">APPROVE WITH CONDITION</option>
								<option value="REJECT">REJECT</option>
								<option value="FRAUD_INVESTIGATION">FRAUD INVESTIGATION</option>
							</select>
						</label>
						<div class="grid grid-cols-2 gap-3">
							<label class="block">
								Approved limit
								<input
									class="mt-1 w-full rounded border-slate-300 text-sm"
									type="number"
									bind:value={form.approved_limit}
								/>
							</label>
							<label class="block">
								Approved tenor (months)
								<input
									class="mt-1 w-full rounded border-slate-300 text-sm"
									type="number"
									bind:value={form.approved_tenor_months}
								/>
							</label>
						</div>
						<label class="block">
							Reason code (required for reject)
							<select
								class="mt-1 w-full rounded border-slate-300 text-sm"
								bind:value={form.override_reason_code}
							>
								<option value="">— none —</option>
								{#each reasonCodes as rc (rc.code)}
									<option value={rc.code}>{rc.code}</option>
								{/each}
							</select>
						</label>
						<label class="block">
							Override reason (required when decision differs from system)
							<textarea
								class="mt-1 h-16 w-full rounded border-slate-300 text-sm"
								bind:value={form.override_reason}></textarea>
						</label>
						<label class="block">
							Notes
							<textarea
								class="mt-1 h-16 w-full rounded border-slate-300 text-sm"
								bind:value={form.notes}></textarea>
						</label>
						<button
							class="w-full rounded bg-slate-900 py-2 text-sm font-semibold text-white"
							type="submit"
						>
							Submit analyst decision
						</button>
					</form>
				</Card>

				<Card title="Other actions">
					<div class="space-y-3 text-xs font-semibold text-slate-600">
						<div>
							<label class="block"
								>Escalation reason
								<input
									class="mt-1 w-full rounded border-slate-300 text-sm"
									bind:value={escalateReason}
								/>
							</label>
							<button
								class="mt-1 rounded bg-purple-700 px-3 py-1.5 text-xs font-semibold text-white"
								onclick={() => act('escalate', { reason: escalateReason })}>Escalate</button
							>
						</div>
						<div>
							<label class="block"
								>Document request message
								<input
									class="mt-1 w-full rounded border-slate-300 text-sm"
									bind:value={documentMessage}
								/>
							</label>
							<button
								class="mt-1 rounded bg-slate-600 px-3 py-1.5 text-xs font-semibold text-white"
								onclick={() => act('request-documents', { message: documentMessage })}
								>Request documents</button
							>
						</div>
						{#if !detail.assigned_to}
							<button
								class="rounded bg-slate-200 px-3 py-1.5 text-xs font-semibold"
								onclick={() => act('assign', {})}>Assign to me</button
							>
						{/if}
					</div>
				</Card>
			{/if}
			{#if actionError}
				<ErrorNote error={actionError} />
			{/if}
		</div>
	</div>
{:else}
	<p class="mt-3 text-sm text-slate-500">Loading…</p>
{/if}
