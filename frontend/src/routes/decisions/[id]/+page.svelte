<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import type { DecisionResponse, TraceResponse } from '$lib/api/types';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import { formatCurrency, formatDateTime, formatPercent } from '$lib/format';

	let decision = $state<DecisionResponse | null>(null);
	let trace = $state<TraceResponse | null>(null);
	let error = $state<unknown>(null);
	let traceError = $state<unknown>(null);
	let expandedStep = $state<number | null>(null);

	function conditionText(step: TraceResponse['steps'][number]): string {
		const conditions = Array.isArray(step.evaluated_conditions)
			? (step.evaluated_conditions as { field?: string; operator?: string; expected?: unknown }[])
			: [];
		if (!conditions.length) return step.name;
		return conditions
			.map(
				(condition) =>
					`${condition.field ?? '?'} ${condition.operator ?? ''} ${JSON.stringify(condition.expected)}`
			)
			.join(' AND ');
	}

	function actionText(action: Record<string, unknown>): string {
		if (action.type === 'SET_OUTPUT')
			return `${action.target ?? 'output'} = ${JSON.stringify(action.value)}`;
		if (action.decision) return `${action.type}: ${action.decision}`;
		return [action.type, action.reason_code].filter(Boolean).join(' · ');
	}

	$effect(() => {
		const id = page.params.id;
		api<DecisionResponse>(`/v1/decisions/${id}`)
			.then((d) => (decision = d))
			.catch((err) => (error = err));
		api<TraceResponse>(`/v1/decisions/${id}/trace`)
			.then((t) => (trace = t))
			.catch((err) => (traceError = err));
	});
</script>

<a class="text-xs text-blue-700 underline" href="/decisions">← Back to decision history</a>

{#if error}
	<div class="mt-3"><ErrorNote {error} /></div>
{:else if decision}
	<div class="mt-2 mb-4 flex items-center gap-3">
		<h1 class="text-xl font-bold text-slate-800">{decision.decision_id}</h1>
		<Badge value={decision.decision} kind="decision" />
		<Badge value={decision.execution_mode} />
	</div>

	<div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
		<Card title="Final decision">
			<dl class="space-y-1.5 text-sm" data-testid="decision-summary">
				<div class="flex justify-between">
					<dt class="text-slate-500">Application</dt>
					<dd class="font-mono text-xs">{decision.application_id}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Strategy version</dt>
					<dd>{decision.strategy_version}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Risk grade</dt>
					<dd>{decision.risk_grade ?? '—'}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Score</dt>
					<dd>{decision.score ?? '—'}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Approved limit</dt>
					<dd>{formatCurrency(decision.approved_limit)}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Approved tenor</dt>
					<dd>
						{decision.approved_tenor_months ? `${decision.approved_tenor_months} months` : '—'}
					</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Pricing rate</dt>
					<dd>{decision.pricing_rate !== null ? formatPercent(decision.pricing_rate, 2) : '—'}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Executed</dt>
					<dd>{formatDateTime(decision.created_at)}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-slate-500">Manual review case</dt>
					<dd>
						{#if decision.manual_review_case_id}
							<a
								class="text-blue-700 underline"
								href="/manual-review/{decision.manual_review_case_id}"
								>{decision.manual_review_case_id}</a
							>
						{:else}—{/if}
					</dd>
				</div>
			</dl>
		</Card>

		<Card title="Reason codes">
			{#if decision.reason_codes.length === 0}
				<p class="text-sm text-slate-500">No reason codes.</p>
			{:else}
				<ul class="space-y-2 text-sm">
					{#each decision.reason_codes as reason (reason.code)}
						<li>
							<span class="font-mono text-xs font-semibold text-slate-800">{reason.code}</span>
							<p class="text-xs text-slate-500">{reason.message}</p>
						</li>
					{/each}
				</ul>
			{/if}
		</Card>

		<Card title="Runtime metadata">
			{#if trace}
				<dl class="space-y-1.5 text-sm">
					<div class="flex justify-between">
						<dt class="text-slate-500">Trace ID</dt>
						<dd class="font-mono text-xs">{trace.trace_id}</dd>
					</div>
					<div class="flex justify-between">
						<dt class="text-slate-500">Latency</dt>
						<dd>{trace.metadata.latency_ms} ms</dd>
					</div>
					<div class="flex justify-between">
						<dt class="text-slate-500">Request ID</dt>
						<dd class="max-w-44 truncate font-mono text-[10px]">
							{trace.metadata.request_id ?? '—'}
						</dd>
					</div>
					<div class="flex justify-between">
						<dt class="text-slate-500">Correlation ID</dt>
						<dd class="max-w-44 truncate font-mono text-[10px]">
							{trace.metadata.correlation_id ?? '—'}
						</dd>
					</div>
				</dl>
			{:else if traceError}
				<ErrorNote error={traceError} />
			{:else}
				<p class="text-sm text-slate-500">Loading trace…</p>
			{/if}
		</Card>
	</div>

	{#if trace}
		<div class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
			<Card
				title="Strategy execution timeline ({trace.strategy.strategy_code} v{trace.strategy
					.version})"
			>
				{#if trace.strategy.strategy_id}
					<a
						class="mb-3 inline-block text-xs font-semibold text-blue-700 underline"
						href="/strategies/{trace.strategy.strategy_id}?version={trace.strategy.version_id ??
							''}">View executed flow →</a
					>
				{/if}
				<ol class="space-y-2" data-testid="trace-steps">
					{#each trace.steps as step (step.order)}
						<li class="rounded border border-slate-200">
							<button
								class="flex w-full items-center justify-between px-3 py-2 text-left text-sm"
								onclick={() => (expandedStep = expandedStep === step.order ? null : step.order)}
							>
								<span>
									<span class="mr-2 font-mono text-xs text-slate-400">#{step.order}</span>
									<span class="font-medium text-slate-800">{step.name}</span>
									{#if step.node_key}<span
											class="ml-2 rounded bg-slate-100 px-1 font-mono text-[10px] text-slate-500"
											>{step.node_key}</span
										>{/if}
									<span class="ml-2 text-xs text-slate-400"
										>{step.type}{step.reference_version ? ` v${step.reference_version}` : ''}</span
									>
									{#if step.type === 'CONDITION'}<span
											class="ml-2 text-xs font-semibold {step.taken_edge === 'TRUE'
												? 'text-emerald-600'
												: 'text-red-600'}">→ {step.taken_edge}</span
										>{/if}
								</span>
								<span class="flex items-center gap-2">
									<Badge value={step.status} />
									<span class="text-xs text-slate-400">{step.duration_ms} ms</span>
								</span>
							</button>
							{#if expandedStep === step.order}
								<div class="border-t border-slate-100 px-3 py-2">
									{#if step.type === 'CONDITION'}
										<div class="rounded bg-slate-50 p-2 text-xs">
											<span class="font-semibold">Condition:</span>
											{conditionText(step)}
											<span
												class="font-bold {step.taken_edge === 'TRUE'
													? 'text-emerald-600'
													: 'text-red-600'}">→ {step.taken_edge}</span
											>
										</div>
									{:else if step.rule_results?.length}
										<table class="w-full text-xs">
											<thead class="text-left text-slate-400">
												<tr
													><th class="py-1 pr-2">Rule</th><th class="py-1 pr-2">v</th><th
														class="py-1 pr-2">Matched</th
													><th class="py-1">Conditions (expected vs actual)</th></tr
												>
											</thead>
											<tbody class="align-top">
												{#each step.rule_results as rule (rule.rule_code)}
													<tr class="border-t border-slate-100">
														<td class="py-1 pr-2 font-mono">{rule.rule_code}</td>
														<td class="py-1 pr-2">{rule.version}</td>
														<td class="py-1 pr-2">
															{rule.matched ? 'YES' : 'no'}
															{#if rule.matched_branch !== undefined && rule.matched_branch !== null}
																<div class="text-[10px] text-blue-700">
																	{rule.matched_branch === 'default'
																		? 'ELSE'
																		: `branch ${Number(rule.matched_branch) + 1}`}
																</div>
															{/if}
														</td>
														<td class="py-1 font-mono text-[11px]">
															{#each rule.evaluated_conditions as cond, index (index)}
																<div>
																	{cond.field}
																	{cond.operator}
																	{JSON.stringify(cond.expected)} → {JSON.stringify(cond.actual)}
																	<span class={cond.result ? 'text-emerald-600' : 'text-slate-400'}
																		>{cond.result ? '✓' : '✗'}</span
																	>
																</div>
															{/each}
															{#if rule.actions_applied?.length}
																<div class="mt-1 border-t border-slate-100 pt-1 text-blue-700">
																	{#each rule.actions_applied as action, actionIndex (actionIndex)}
																		<div>↳ {actionText(action)}</div>
																	{/each}
																</div>
															{:else if rule.action_applied}
																<div class="mt-1 border-t border-slate-100 pt-1 text-blue-700">
																	↳ {actionText(rule.action_applied)}
																</div>
															{/if}
														</td>
													</tr>
												{/each}
											</tbody>
										</table>
									{:else}
										<JsonBlock value={step} maxHeight="16rem" />
									{/if}
								</div>
							{/if}
						</li>
					{/each}
				</ol>
			</Card>

			<div class="space-y-4">
				<Card title="Outputs">
					<JsonBlock value={trace.outputs} maxHeight="12rem" />
				</Card>
				<Card title="Calculated features">
					<JsonBlock value={trace.feature_values} maxHeight="14rem" />
				</Card>
				<Card title="Input snapshot (masked)">
					<JsonBlock value={trace.input_snapshot} maxHeight="18rem" />
				</Card>
			</div>
		</div>
	{/if}
{:else}
	<p class="mt-3 text-sm text-slate-500">Loading…</p>
{/if}
