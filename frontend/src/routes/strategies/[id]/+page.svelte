<script lang="ts">
	import { page } from '$app/state';
	import {
		Background,
		BackgroundVariant,
		Controls,
		MiniMap,
		SvelteFlow,
		type Connection
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { api, ApiError } from '$lib/api/client';
	import type {
		ConfigEntity,
		Meta,
		Rule,
		RuleSet,
		Strategy,
		StrategyVersion
	} from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ConditionBuilder from '$lib/components/ConditionBuilder.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import { autoLayout } from '$lib/flow/layout';
	import {
		connectionToEdge,
		flowToGraph,
		graphToFlow,
		validateFlowGraph,
		type GraphIssue
	} from '$lib/flow/serializers';
	import StrategyNodeComponent from '$lib/flow/StrategyNode.svelte';
	import {
		defaultGraphNode,
		EDITABLE_NODE_TYPES,
		type StrategyFlowEdge,
		type StrategyFlowNode
	} from '$lib/flow/types';
	import { builderConditionToJson, jsonToBuilder, type BuilderCondition } from '$lib/rule-format';

	const nodeTypes = { strategy: StrategyNodeComponent };
	let strategy = $state<Strategy | null>(null);
	let meta = $state<Meta | null>(null);
	let ruleSets = $state<RuleSet[]>([]);
	let rules = $state<Rule[]>([]);
	let scorecards = $state<ConfigEntity[]>([]);
	let decisionTables = $state<ConfigEntity[]>([]);
	let error = $state<unknown>(null);
	let actionError = $state<unknown>(null);
	let selected = $state<StrategyVersion | null>(null);
	let nodes = $state.raw<StrategyFlowNode[]>([]);
	let edges = $state.raw<StrategyFlowEdge[]>([]);
	let selectedNodeId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let issues = $state<GraphIssue[]>([]);
	let editorNote = $state('');
	let rollbackReason = $state('');
	let submitSimId = $state('');
	let conditionState = $state<BuilderCondition>({
		kind: 'group',
		logic: 'all',
		children: [{ kind: 'condition', field: '', operator: '=', value: '', negated: false }],
		negated: false
	});

	const canCreate = $derived(auth.hasPermission('strategy.create'));
	const canActivate = $derived(auth.hasPermission('strategy.activate'));
	const editable = $derived(Boolean(canCreate && selected?.status === 'DRAFT'));
	const selectedNode = $derived(nodes.find((node) => node.id === selectedNodeId) ?? null);
	const selectedEdge = $derived(edges.find((edge) => edge.id === selectedEdgeId) ?? null);
	const ruleIdsByCode = $derived(new Map(rules.map((rule) => [rule.rule_code, rule.id])));
	const selectedRuleSet = $derived(
		selectedNode?.data.nodeType === 'RULE_SET'
			? (ruleSets.find((item) => item.code === selectedNode.data.referenceCode) ?? null)
			: null
	);
	const selectedTableId = $derived(
		selectedNode?.data.nodeType === 'DECISION_TABLE'
			? (decisionTables.find((item) => item.code === selectedNode.data.referenceCode)?.id ?? null)
			: null
	);
	const referenceOptions = $derived.by(() => {
		if (!selectedNode) return [] as { code: string; label: string }[];
		if (selectedNode.data.nodeType === 'RULE_SET') {
			return ruleSets.map((item) => ({ code: item.code, label: `${item.code} — ${item.name}` }));
		}
		if (selectedNode.data.nodeType === 'SCORECARD') {
			return scorecards.map((item) => ({ code: item.code, label: `${item.code} — ${item.name}` }));
		}
		if (selectedNode.data.nodeType === 'DECISION_TABLE') {
			return decisionTables.map((item) => ({
				code: item.code,
				label: `${item.code} — ${item.name}`
			}));
		}
		return [];
	});

	function applyVersion(version: StrategyVersion | null) {
		selected = version;
		const flow = graphToFlow(version?.graph, version?.status !== 'DRAFT');
		nodes = flow.nodes;
		edges = flow.edges;
		selectedNodeId = null;
		selectedEdgeId = null;
		issues = [];
		editorNote = version?.version_note ?? '';
	}

	async function load() {
		error = null;
		try {
			const [strategyResult, metaResult, ruleSetResult, ruleResult, scorecardResult, tableResult] =
				await Promise.all([
					api<Strategy>(`/v1/strategies/${page.params.id}`),
					api<Meta>('/v1/meta'),
					api<RuleSet[]>('/v1/rule-sets'),
					api<Rule[]>('/v1/rules'),
					api<ConfigEntity[]>('/v1/scorecards'),
					api<ConfigEntity[]>('/v1/decision-tables')
				]);
			strategy = strategyResult;
			meta = metaResult;
			ruleSets = ruleSetResult;
			rules = ruleResult;
			scorecards = scorecardResult;
			decisionTables = tableResult;
			const versions = strategy.versions ?? [];
			const requestedVersionId = page.url.searchParams.get('version');
			applyVersion(
				versions.find((version) => version.id === requestedVersionId) ??
					versions.find((version) => version.id === selected?.id) ??
					versions[versions.length - 1] ??
					null
			);
		} catch (err) {
			error = err;
		}
	}

	$effect(() => {
		load();
	});

	function chooseVersion(version: StrategyVersion) {
		applyVersion(version);
	}

	function setSelectedNode(node: StrategyFlowNode | null) {
		selectedNodeId = node?.id ?? null;
		selectedEdgeId = null;
		if (node?.data.nodeType === 'CONDITION') {
			const parsed = jsonToBuilder({
				rule_kind: 'STATEMENT',
				condition: node.data.config.condition,
				action: { type: 'SET_OUTPUT', target: 'outputs._preview', value: true }
			});
			if (parsed.state?.branches[0]) conditionState = parsed.state.branches[0].when;
		}
	}

	function patchSelectedNode(patch: Partial<StrategyFlowNode['data']>) {
		if (!selectedNodeId || !editable) return;
		nodes = nodes.map((node) =>
			node.id === selectedNodeId ? { ...node, data: { ...node.data, ...patch } } : node
		);
	}

	function patchConfig(key: string, value: unknown) {
		if (!selectedNode) return;
		patchSelectedNode({ config: { ...selectedNode.data.config, [key]: value } });
	}

	function selectedConfigList(key: string): string[] {
		const value = selectedNode?.data.config[key];
		return Array.isArray(value) ? value.map(String) : [];
	}

	function toggleConfigList(key: string, value: string, checked: boolean) {
		const current = selectedConfigList(key).filter((item) => item !== value);
		patchConfig(key, checked ? [...current, value] : current);
	}

	function addNode(nodeType: string, position = { x: 200, y: 100 }) {
		if (!editable) return;
		const base = nodeType.toLowerCase().replaceAll('_', '-');
		let index = 1;
		let id = `${base}-${index}`;
		while (nodes.some((node) => node.id === id)) id = `${base}-${++index}`;
		const graphNode = defaultGraphNode(nodeType, id, position);
		const flow = graphToFlow({ nodes: [graphNode], edges: [] });
		nodes = [...nodes, flow.nodes[0]];
		setSelectedNode(flow.nodes[0]);
	}

	function dropNode(event: DragEvent) {
		event.preventDefault();
		const nodeType = event.dataTransfer?.getData('application/oscar-node');
		if (!nodeType) return;
		const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
		addNode(nodeType, { x: event.clientX - rect.left - 80, y: event.clientY - rect.top - 30 });
	}

	function connect(connection: Connection) {
		if (!editable) return;
		const sourceNode = nodes.find((node) => node.id === connection.source);
		const label = connection.sourceHandle?.toUpperCase() ?? null;
		if (sourceNode?.data.nodeType === 'CONDITION' && !label) return;
		const occupied = edges.find(
			(edge) =>
				edge.source === connection.source &&
				String(edge.label ?? '').toUpperCase() === String(label ?? '').toUpperCase()
		);
		if (occupied && !confirm(`Replace the existing ${label ?? 'outgoing'} edge?`)) return;
		edges = [...edges.filter((edge) => edge.id !== occupied?.id), connectionToEdge(connection)];
	}

	function deleteSelectedNode() {
		if (!selectedNode || !editable || selectedNode.data.nodeType === 'START') return;
		// Capture the id first: the $derived selectedNode turns null as soon as nodes is filtered.
		const nodeId = selectedNode.id;
		nodes = nodes.filter((node) => node.id !== nodeId);
		edges = edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
		selectedNodeId = null;
	}

	function deleteSelectedEdge() {
		if (!selectedEdge || !editable) return;
		const edgeId = selectedEdge.id;
		edges = edges.filter((edge) => edge.id !== edgeId);
		selectedEdgeId = null;
	}

	function layout() {
		nodes = autoLayout(nodes, edges);
	}

	function validate(): boolean {
		issues = validateFlowGraph(nodes, edges);
		const invalid = new Set(issues.flatMap((issue) => (issue.nodeKey ? [issue.nodeKey] : [])));
		nodes = nodes.map((node) => ({
			...node,
			data: { ...node.data, invalid: invalid.has(node.id) }
		}));
		return issues.length === 0;
	}

	async function saveGraph(asNewVersion: boolean) {
		if (!strategy || !selected || !validate()) return;
		actionError = null;
		try {
			const body = { graph: flowToGraph(nodes, edges), version_note: editorNote };
			if (asNewVersion) {
				const created = await api<StrategyVersion>(`/v1/strategies/${strategy.id}/versions`, {
					body
				});
				await load();
				const draft = (strategy?.versions ?? []).find((version) => version.id === created.id);
				if (draft) applyVersion(draft);
			} else {
				await api(`/v1/strategies/${strategy.id}/versions/${selected.id}`, {
					method: 'PUT',
					body
				});
				await load();
			}
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Could not save the flow');
			if (err instanceof ApiError) {
				issues = err.details.map((detail) => ({
					field: detail.field ?? 'graph',
					issue: detail.issue ?? err.message
				}));
			}
		}
	}

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

	async function submitForApproval() {
		if (!strategy || !selected || !validate()) return;
		actionError = null;
		try {
			let simulationId = submitSimId.trim();
			if (!simulationId) {
				const sim = await api<{ simulation_id: string }>('/v1/simulations/single', {
					body: {
						application_payload: {
							application_id: 'APP-SUBMIT-SIM',
							product_type: strategy.product_type,
							segment: strategy.segment,
							applicant: { age: 34, monthly_income: 8500000, existing_monthly_obligation: 2500000 },
							loan: { requested_amount: 15000000, requested_tenor_months: 24 },
							vehicle: { type: 'MOTOR', year: 2020, appraisal_value: 18000000 },
							fraud: { identity_match: true, document_match: true, blacklist_hit: false },
							model_outputs: { credit_score: 684, model_version: 'MOTOR_SCORE_V1' }
						},
						strategy_version_id: selected.id
					}
				});
				simulationId = sim.simulation_id;
			}
			await api(`/v1/strategies/${strategy.id}/versions/${selected.id}/submit-approval`, {
				body: { simulation_id: simulationId }
			});
			submitSimId = '';
			await load();
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Could not submit for approval');
		}
	}
</script>

<a class="text-xs text-blue-700 underline" href="/strategies">← Back to strategies</a>

{#if error}
	<div class="mt-3"><ErrorNote {error} /></div>
{:else if strategy}
	<div class="mt-2 mb-4 flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-xl font-bold text-slate-800">{strategy.strategy_code}</h1>
			<p class="text-sm text-slate-500">
				{strategy.name} · {strategy.product_type} / {strategy.segment}
			</p>
		</div>
		{#if selected}
			<div class="flex items-center gap-2">
				<span class="text-sm">v{selected.version}</span><Badge value={selected.status} />
			</div>
		{/if}
	</div>

	<div class="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-4">
		<Card title="Versions">
			<ul class="max-h-52 space-y-1 overflow-auto">
				{#each strategy.versions ?? [] as version (version.id)}
					<li>
						<button
							class="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm {selected?.id ===
							version.id
								? 'bg-slate-100 font-semibold'
								: 'hover:bg-slate-50'}"
							onclick={() => chooseVersion(version)}
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
		</Card>

		<div class="xl:col-span-3">
			<Card title="Lifecycle & validation">
				<div class="flex flex-wrap items-end gap-2">
					{#if editable}
						<button
							class="rounded bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => saveGraph(false)}>Save draft</button
						>
						<button
							class="rounded bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => saveGraph(true)}>Save as new version</button
						>
						<button
							class="rounded bg-slate-200 px-3 py-1.5 text-xs font-semibold"
							onclick={validate}>Validate</button
						>
						<button class="rounded bg-slate-200 px-3 py-1.5 text-xs font-semibold" onclick={layout}
							>Auto-layout</button
						>
						<button
							class="rounded bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={submitForApproval}>Submit for approval</button
						>
						<input
							class="min-w-64 rounded border-slate-300 text-xs"
							placeholder="optional SIM id (else auto-run)"
							bind:value={submitSimId}
						/>
					{:else if canCreate && selected && ['ACTIVE', 'RETIRED', 'REJECTED'].includes(selected.status)}
						<button
							class="rounded bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => saveGraph(true)}>Start new draft from this flow</button
						>
					{/if}
					{#if canActivate && selected?.status === 'PENDING_APPROVAL'}
						<button
							class="rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => lifecycle('activate', 'Activated via workbench')}
							>Approve &amp; activate</button
						>
						<button
							class="rounded bg-red-600 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => lifecycle('reject', 'Rejected via workbench')}>Reject</button
						>
					{/if}
					{#if canActivate && selected?.status === 'RETIRED'}
						<input
							class="rounded border-slate-300 text-xs"
							placeholder="rollback reason"
							bind:value={rollbackReason}
						/>
						<button
							class="rounded bg-purple-700 px-3 py-1.5 text-xs font-semibold text-white"
							onclick={() => lifecycle('rollback', rollbackReason)}>Rollback</button
						>
					{/if}
				</div>
				<label class="mt-3 block text-xs font-semibold text-slate-600"
					>Version note <input
						class="mt-1 w-full rounded border-slate-300 text-sm"
						bind:value={editorNote}
						disabled={!editable}
					/></label
				>
				{#if issues.length}
					<div class="mt-3 rounded border border-red-200 bg-red-50 p-3" data-testid="graph-issues">
						<div class="text-xs font-bold text-red-700">Flow issues ({issues.length})</div>
						<ul class="mt-1 list-disc pl-5 text-xs text-red-700">
							{#each issues as issue, index (`${issue.nodeKey ?? issue.field}:${index}`)}<li>
									{issue.nodeKey ? `${issue.nodeKey}: ` : ''}{issue.issue}
								</li>{/each}
						</ul>
					</div>
				{/if}
				{#if actionError}<div class="mt-3"><ErrorNote error={actionError} /></div>{/if}
			</Card>
		</div>
	</div>

	<div class="grid grid-cols-1 gap-4 xl:grid-cols-[180px_minmax(0,1fr)_300px]">
		<Card title="Node palette">
			<p class="mb-2 text-[11px] text-slate-400">Drag onto the canvas or click to add.</p>
			<div class="space-y-1.5">
				{#each EDITABLE_NODE_TYPES as nodeType (nodeType)}
					<button
						draggable={editable}
						ondragstart={(event) => event.dataTransfer?.setData('application/oscar-node', nodeType)}
						onclick={() => addNode(nodeType)}
						disabled={!editable}
						class="w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
						>{nodeType.replaceAll('_', ' ')}</button
					>
				{/each}
			</div>
		</Card>

		<div
			class="h-[650px] overflow-hidden rounded-lg border border-slate-200 bg-white"
			ondragover={(event) => event.preventDefault()}
			ondrop={dropNode}
			data-testid="strategy-flow-canvas"
			role="application"
			aria-label="Strategy flow canvas"
		>
			{#if selected}
				{#key selected.id}
					<SvelteFlow
						bind:nodes
						bind:edges
						{nodeTypes}
						fitView
						nodesDraggable={editable}
						nodesConnectable={editable}
						elementsSelectable={true}
						deleteKey={editable ? 'Backspace' : null}
						onconnect={connect}
						onnodeclick={({ node }) => setSelectedNode(node as StrategyFlowNode)}
						onedgeclick={({ edge }) => {
							selectedEdgeId = edge.id;
							selectedNodeId = null;
						}}
						onpaneclick={() => setSelectedNode(null)}
						defaultEdgeOptions={{ type: 'smoothstep' }}
					>
						<Background variant={BackgroundVariant.Dots} />
						<Controls />
						<MiniMap pannable zoomable />
					</SvelteFlow>
				{/key}
			{/if}
		</div>

		<Card title="Node configuration">
			{#if selectedNode}
				<div class="space-y-3 text-xs">
					<div class="flex items-center justify-between">
						<Badge
							value={selectedNode.data.nodeType}
						/>{#if editable && selectedNode.data.nodeType !== 'START'}<button
								class="text-red-600 underline"
								onclick={deleteSelectedNode}>Delete</button
							>{/if}
					</div>
					<label class="block font-semibold text-slate-600"
						>Name <input
							class="mt-1 w-full rounded border-slate-300 text-sm"
							value={selectedNode.data.name}
							disabled={!editable}
							oninput={(event) => patchSelectedNode({ name: event.currentTarget.value })}
						/></label
					>
					{#if referenceOptions.length}
						<label class="block font-semibold text-slate-600"
							>Reference <select
								class="mt-1 w-full rounded border-slate-300 text-sm"
								value={selectedNode.data.referenceCode ?? ''}
								disabled={!editable}
								onchange={(event) =>
									patchSelectedNode({ referenceCode: event.currentTarget.value || null })}
								><option value="">Select…</option
								>{#each referenceOptions as option (option.code)}<option value={option.code}
										>{option.label}</option
									>{/each}</select
							></label
						>
					{/if}
					{#if selectedRuleSet}
						<div class="rounded border border-slate-200 p-2" data-testid="node-rule-links">
							<div class="mb-1 font-semibold text-slate-600">
								Rules in {selectedRuleSet.code}
							</div>
							<ul class="space-y-1">
								{#each selectedRuleSet.rule_codes as ruleCode (ruleCode)}
									<li class="flex items-center justify-between gap-2">
										<span class="truncate font-mono text-[11px]">{ruleCode}</span>
										{#if ruleIdsByCode.get(ruleCode)}
											<a
												class="shrink-0 text-blue-700 underline"
												href={`/rules/${ruleIdsByCode.get(ruleCode)}`}>Open rule →</a
											>
										{/if}
									</li>
								{/each}
							</ul>
							<p class="mt-2 text-[10px] text-slate-400">
								Editing a rule creates a new rule version through its own approval flow.
							</p>
						</div>
					{:else if selectedNode.data.nodeType === 'DECISION_TABLE' && selectedTableId}
						<a
							class="block text-blue-700 underline"
							data-testid="node-open-table"
							href={`/decision-tables/${selectedTableId}`}>Open table editor →</a
						>
					{:else if selectedNode.data.nodeType === 'SCORECARD'}
						<p class="text-[11px] text-slate-500">
							Score bands are versioned via the scorecard API. Model versions are documented in
							<a class="text-blue-700 underline" href="/models">Model Registry</a>.
						</p>
					{/if}
					{#if !['START', 'END'].includes(selectedNode.data.nodeType)}
						<label class="block font-semibold text-slate-600"
							>On error <select
								class="mt-1 w-full rounded border-slate-300 text-sm"
								value={selectedNode.data.onError}
								disabled={!editable}
								onchange={(event) => patchSelectedNode({ onError: event.currentTarget.value })}
								>{#each meta?.step_on_error ?? ['FAIL', 'SKIP', 'MANUAL_REVIEW'] as value (value)}<option
										{value}>{value}</option
									>{/each}</select
							></label
						>
					{/if}
					{#if selectedNode.data.nodeType === 'VALIDATION'}
						<fieldset class="max-h-56 overflow-auto rounded border border-slate-200 p-2">
							<legend class="font-semibold">Required fields</legend
							>{#each meta?.features ?? [] as feature (feature.path)}<label
									class="flex items-center gap-2 py-1"
									><input
										type="checkbox"
										checked={selectedConfigList('required_fields').includes(feature.path)}
										disabled={!editable}
										onchange={(event) =>
											toggleConfigList(
												'required_fields',
												feature.path,
												event.currentTarget.checked
											)}
									/> <span>{feature.path}</span></label
								>{/each}
						</fieldset>
					{:else if selectedNode.data.nodeType === 'CALCULATION'}
						<fieldset class="max-h-56 overflow-auto rounded border border-slate-200 p-2">
							<legend class="font-semibold">Derived calculations</legend
							>{#each (meta?.features ?? []).filter((feature) => feature.derived) as feature (feature.path)}<label
									class="flex items-center gap-2 py-1"
									><input
										type="checkbox"
										checked={selectedConfigList('derived_features').includes(feature.path)}
										disabled={!editable}
										onchange={(event) =>
											toggleConfigList(
												'derived_features',
												feature.path,
												event.currentTarget.checked
											)}
									/> <span>{feature.path}</span></label
								>{/each}
						</fieldset>
					{:else if selectedNode.data.nodeType === 'CONDITION'}
						<div class="rounded border border-slate-200 p-2">
							<ConditionBuilder {meta} bind:condition={conditionState} /><button
								class="mt-2 rounded bg-slate-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
								disabled={!editable}
								onclick={() => patchConfig('condition', builderConditionToJson(conditionState))}
								>Apply condition</button
							>
						</div>
					{:else if Object.keys(selectedNode.data.config).length}
						<pre class="max-h-48 overflow-auto rounded bg-slate-50 p-2 text-[10px]">{JSON.stringify(
								selectedNode.data.config,
								null,
								2
							)}</pre>
					{/if}
				</div>
			{:else if selectedEdge}
				<div class="space-y-3 text-xs" data-testid="edge-config">
					<div class="flex items-center justify-between">
						<Badge value={selectedEdge.label ? `EDGE ${selectedEdge.label}` : 'EDGE'} />
						{#if editable}<button class="text-red-600 underline" onclick={deleteSelectedEdge}
								>Delete edge</button
							>{/if}
					</div>
					<p class="text-slate-600">
						<span class="font-mono">{selectedEdge.source}</span> →
						<span class="font-mono">{selectedEdge.target}</span>
					</p>
					{#if editable}
						<p class="text-[11px] text-slate-400">
							To reroute, delete this edge and drag a new connection between node handles.
						</p>
					{/if}
				</div>
			{:else}
				<p class="text-xs text-slate-500">
					Click a node to inspect or configure it, or click an edge to manage the connection.
				</p>
				{#if editable}
					<p class="mt-2 text-[11px] text-slate-400">
						Drag from a node's right handle to another node to connect them. Select an element and
						press Backspace to delete it.
					</p>
				{:else if selected}
					<div
						class="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-800"
						data-testid="readonly-note"
					>
						This {selected.status} version is immutable. Use “Start new draft from this flow” to make
						changes, then submit the draft for approval.
					</div>
				{/if}
			{/if}
		</Card>
	</div>
{:else}
	<p class="mt-3 text-sm text-slate-500">Loading…</p>
{/if}

<style>
	:global(.edge-true .svelte-flow__edge-path) {
		stroke: #16a34a;
	}
	:global(.edge-false .svelte-flow__edge-path) {
		stroke: #dc2626;
	}
	:global(.svelte-flow__edge-text) {
		font-size: 10px;
		font-weight: 700;
	}
</style>
