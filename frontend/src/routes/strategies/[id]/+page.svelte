<script lang="ts">
	import { appPath } from '$lib/app-path';

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
	import ConditionBuilder from '$lib/components/ConditionBuilder.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import { confirmAction } from '$lib/ui/confirm';
	import { toast } from 'svelte-sonner';
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
	let submitSimId = $state('');
	let paletteOpen = $state(true);
	let inspectorOpen = $state(true);
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

	async function connect(connection: Connection) {
		if (!editable) return;
		const sourceNode = nodes.find((node) => node.id === connection.source);
		const label = connection.sourceHandle?.toUpperCase() ?? null;
		if (sourceNode?.data.nodeType === 'CONDITION' && !label) return;
		const occupied = edges.find(
			(edge) =>
				edge.source === connection.source &&
				String(edge.label ?? '').toUpperCase() === String(label ?? '').toUpperCase()
		);
		if (occupied) {
			const confirmation = await confirmAction({
				title: 'Replace existing edge?',
				body: `The current ${label ?? 'outgoing'} connection will be replaced.`,
				confirmLabel: 'Replace'
			});
			if (!confirmation.ok) return;
		}
		edges = [...edges.filter((edge) => edge.id !== occupied?.id), connectionToEdge(connection)];
	}

	async function deleteSelectedNode() {
		if (!selectedNode || !editable || selectedNode.data.nodeType === 'START') return;
		const confirmation = await confirmAction({
			title: 'Delete flow node?',
			body: `${selectedNode.data.name || selectedNode.id} and its connected edges will be removed from this draft.`,
			confirmLabel: 'Delete node',
			tone: 'danger'
		});
		if (!confirmation.ok) return;
		// Capture the id first: the $derived selectedNode turns null as soon as nodes is filtered.
		const nodeId = selectedNode.id;
		nodes = nodes.filter((node) => node.id !== nodeId);
		edges = edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
		selectedNodeId = null;
	}

	async function deleteSelectedEdge() {
		if (!selectedEdge || !editable) return;
		const confirmation = await confirmAction({
			title: 'Delete flow edge?',
			body: `${selectedEdge.source} → ${selectedEdge.target}`,
			confirmLabel: 'Delete edge',
			tone: 'danger'
		});
		if (!confirmation.ok) return;
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
			toast.success(asNewVersion ? 'Strategy draft version created' : 'Strategy flow saved');
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Could not save the flow');
			toast.error(err instanceof ApiError ? err.message : 'Could not save strategy flow');
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
			toast.success('Strategy lifecycle updated');
		} catch (err) {
			actionError = err;
			toast.error('Could not update strategy lifecycle');
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
			toast.success('Strategy submitted for approval');
		} catch (err) {
			actionError = err instanceof ApiError ? err : new Error('Could not submit for approval');
			toast.error(err instanceof ApiError ? err.message : 'Could not submit strategy for approval');
		}
	}

	async function confirmLifecycle(
		actionPath: string,
		title: string,
		confirmLabel: string,
		tone: 'default' | 'danger' = 'default'
	) {
		const confirmation = await confirmAction({
			title,
			confirmLabel,
			tone,
			requireReason: true
		});
		if (!confirmation.ok) return;
		await lifecycle(actionPath, confirmation.reason ?? '');
	}
</script>

{#if error}
	<div class="mb-4"><ErrorNote {error} /></div>
{:else if strategy}
	<PageHeader
		title={strategy.strategy_code}
		description={`${strategy.name} · ${strategy.product_type} / ${strategy.segment}`}
	>
		{#snippet actions()}
			{#if selected}
				<div class="flex items-center gap-2">
					<StatusBadge value={selected.status} />
					<label class="sr-only" for="strategy-version">Version</label>
					<select
						id="strategy-version"
						class="h-9 rounded-control border border-border bg-surface px-3 text-xs text-text"
						value={selected.id}
						onchange={(event) => {
							const version = strategy?.versions?.find(
								(item) => item.id === event.currentTarget.value
							);
							if (version) chooseVersion(version);
						}}
					>
						{#each strategy?.versions ?? [] as version (version.id)}<option value={version.id}
								>v{version.version} · {version.status}</option
							>{/each}
					</select>
				</div>
			{/if}
		{/snippet}
	</PageHeader>

	<div
		class="sticky top-14 z-30 mb-3 flex flex-wrap items-center justify-between gap-2 rounded-card border border-border bg-surface/95 p-2 shadow-card backdrop-blur"
	>
		<div class="flex flex-wrap items-center gap-2">
			{#if editable}
				<button
					class="rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white hover:bg-primary-700"
					onclick={() => saveGraph(false)}>Save draft</button
				>
				<button
					class="rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted"
					onclick={() => saveGraph(true)}>Save as new version</button
				>
				<button
					class="rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted"
					onclick={validate}>Validate</button
				>
				<button
					class="rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted"
					onclick={layout}>Auto-layout</button
				>
				<button
					class="rounded-control bg-warning px-3 py-2 text-xs font-semibold text-white"
					onclick={submitForApproval}>Submit</button
				>
				<input
					class="h-9 min-w-56 rounded-control border border-border bg-surface px-3 text-xs text-text"
					placeholder="optional SIM id (else auto-run)"
					bind:value={submitSimId}
				/>
			{:else if canCreate && selected && ['ACTIVE', 'RETIRED', 'REJECTED'].includes(selected.status)}
				<button
					class="rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white"
					onclick={() => saveGraph(true)}>Start new draft from this flow</button
				>
			{/if}
			{#if canActivate && selected?.status === 'PENDING_APPROVAL'}
				<button
					class="rounded-control bg-success px-3 py-2 text-xs font-semibold text-white"
					onclick={() =>
						confirmLifecycle('activate', 'Approve and activate strategy?', 'Approve & activate')}
					>Approve & activate</button
				>
				<button
					class="rounded-control bg-danger px-3 py-2 text-xs font-semibold text-white"
					onclick={() => confirmLifecycle('reject', 'Reject strategy version?', 'Reject', 'danger')}
					>Reject</button
				>
			{/if}
			{#if canActivate && selected?.status === 'RETIRED'}
				<button
					class="rounded-control bg-special px-3 py-2 text-xs font-semibold text-white"
					onclick={() =>
						confirmLifecycle('rollback', 'Rollback to this strategy version?', 'Rollback')}
					>Rollback</button
				>
			{/if}
		</div>
		<div class="flex items-center gap-1">
			<button
				class="rounded-control border border-border px-2 py-2 text-xs text-text-muted"
				aria-label="Toggle node palette"
				onclick={() => (paletteOpen = !paletteOpen)}
				>{paletteOpen ? 'Hide palette' : 'Show palette'}</button
			>
			<button
				class="rounded-control border border-border px-2 py-2 text-xs text-text-muted"
				aria-label="Toggle inspector"
				onclick={() => (inspectorOpen = !inspectorOpen)}
				>{inspectorOpen ? 'Hide inspector' : 'Show inspector'}</button
			>
		</div>
	</div>

	{#if actionError}<div class="mb-3"><ErrorNote error={actionError} /></div>{/if}

	<div
		class="grid min-h-[560px] gap-3"
		style={`grid-template-columns:${paletteOpen ? '180px' : '0px'} minmax(0,1fr) ${inspectorOpen ? '320px' : '0px'}`}
	>
		<aside
			class="overflow-hidden transition-all {paletteOpen
				? 'opacity-100'
				: 'pointer-events-none opacity-0'}"
		>
			<div class="h-full rounded-card border border-border bg-surface p-3 shadow-card">
				<h2 class="text-xs font-semibold uppercase tracking-wide text-text-muted">Node palette</h2>
				<p class="mt-1 text-[11px] text-text-faint">Drag onto canvas or click to add.</p>
				<div class="mt-3 space-y-1.5">
					{#each EDITABLE_NODE_TYPES as nodeType (nodeType)}<button
							draggable={editable}
							ondragstart={(event) =>
								event.dataTransfer?.setData('application/oscar-node', nodeType)}
							onclick={() => addNode(nodeType)}
							disabled={!editable}
							class="w-full rounded-control border border-border bg-surface px-2 py-2 text-left text-xs font-semibold text-text hover:bg-surface-muted disabled:opacity-50"
							>{nodeType.replaceAll('_', ' ')}</button
						>{/each}
				</div>
			</div>
		</aside>

		<div
			class="relative h-[calc(100vh-13rem)] min-h-[560px] overflow-hidden rounded-card border border-border bg-surface shadow-card"
			ondragover={(event) => event.preventDefault()}
			ondrop={dropNode}
			data-testid="strategy-flow-canvas"
			role="application"
			aria-label="Strategy flow canvas"
		>
			{#if selected}{#key selected.id}<SvelteFlow
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
						><Background variant={BackgroundVariant.Dots} /><Controls /><MiniMap
							pannable
							zoomable
						/></SvelteFlow
					>{/key}{/if}
			{#if issues.length}<div
					class="absolute inset-x-3 bottom-3 z-30 rounded-card border border-danger/25 bg-danger-bg p-3 shadow-overlay"
					data-testid="graph-issues"
				>
					<div class="flex items-center justify-between">
						<strong class="text-xs text-danger">Flow issues ({issues.length})</strong><button
							class="text-xs text-danger"
							onclick={() => (issues = [])}>Dismiss</button
						>
					</div>
					<ul class="mt-1 list-disc pl-5 text-xs text-danger">
						{#each issues as issue, index (`${issue.nodeKey ?? issue.field}:${index}`)}<li>
								{issue.nodeKey ? `${issue.nodeKey}: ` : ''}{issue.issue}
							</li>{/each}
					</ul>
				</div>{/if}
		</div>

		<aside
			class="overflow-hidden transition-all {inspectorOpen
				? 'opacity-100'
				: 'pointer-events-none opacity-0'}"
		>
			<div
				class="h-[calc(100vh-13rem)] min-h-[560px] overflow-auto rounded-card border border-border bg-surface p-4 shadow-card"
			>
				<h2 class="mb-3 text-sm font-semibold text-text">Inspector</h2>
				<label class="mb-4 block text-xs font-medium text-text-muted"
					>Version note<input
						class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-xs text-text"
						bind:value={editorNote}
						disabled={!editable}
					/></label
				>
				{#if selectedNode}
					<div class="space-y-3 text-xs">
						<div class="flex items-center justify-between">
							<StatusBadge
								value={selectedNode.data.nodeType}
							/>{#if editable && selectedNode.data.nodeType !== 'START'}<button
									class="text-danger"
									onclick={deleteSelectedNode}>Delete node</button
								>{/if}
						</div>
						<label class="block font-medium text-text-muted"
							>Name<input
								class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
								value={selectedNode.data.name}
								disabled={!editable}
								oninput={(event) => patchSelectedNode({ name: event.currentTarget.value })}
							/></label
						>
						{#if referenceOptions.length}<label class="block font-medium text-text-muted"
								>Reference<select
									class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
									value={selectedNode.data.referenceCode ?? ''}
									disabled={!editable}
									onchange={(event) =>
										patchSelectedNode({ referenceCode: event.currentTarget.value || null })}
									><option value="">Select…</option
									>{#each referenceOptions as option (option.code)}<option value={option.code}
											>{option.label}</option
										>{/each}</select
								></label
							>{/if}
						{#if selectedRuleSet}<div
								class="rounded-card border border-border p-3"
								data-testid="node-rule-links"
							>
								<div class="mb-2 font-semibold text-text">Rules in {selectedRuleSet.code}</div>
								<ul class="space-y-1">
									{#each selectedRuleSet.rule_codes as ruleCode (ruleCode)}<li
											class="flex items-center justify-between gap-2"
										>
											<span class="truncate font-mono text-[11px]">{ruleCode}</span
											>{#if ruleIdsByCode.get(ruleCode)}<a
													class="shrink-0 text-primary-700 hover:underline"
													href={appPath(`/rules/${ruleIdsByCode.get(ruleCode)}`)}>Open rule →</a
												>{/if}
										</li>{/each}
								</ul>
							</div>
						{:else if selectedNode.data.nodeType === 'DECISION_TABLE' && selectedTableId}<a
								class="block text-primary-700 hover:underline"
								data-testid="node-open-table"
								href={appPath(`/decision-tables/${selectedTableId}`)}>Open table editor →</a
							>
						{:else if selectedNode.data.nodeType === 'SCORECARD'}<p
								class="text-[11px] text-text-muted"
							>
								Score bands are versioned through scorecards. See <a
									class="text-primary-700 hover:underline"
									href={appPath(`/models`)}>Model Registry</a
								>.
							</p>{/if}
						{#if !['START', 'END'].includes(selectedNode.data.nodeType)}<label
								class="block font-medium text-text-muted"
								>On error<select
									class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-sm text-text"
									value={selectedNode.data.onError}
									disabled={!editable}
									onchange={(event) => patchSelectedNode({ onError: event.currentTarget.value })}
									>{#each meta?.step_on_error ?? ['FAIL', 'SKIP', 'MANUAL_REVIEW'] as value (value)}<option
											{value}>{value}</option
										>{/each}</select
								></label
							>{/if}
						{#if selectedNode.data.nodeType === 'VALIDATION'}<fieldset
								class="max-h-56 overflow-auto rounded-card border border-border p-2"
							>
								<legend class="font-semibold text-text">Required fields</legend
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
										/><span>{feature.path}</span></label
									>{/each}
							</fieldset>
						{:else if selectedNode.data.nodeType === 'CALCULATION'}<fieldset
								class="max-h-56 overflow-auto rounded-card border border-border p-2"
							>
								<legend class="font-semibold text-text">Derived calculations</legend
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
										/><span>{feature.path}</span></label
									>{/each}
							</fieldset>
						{:else if selectedNode.data.nodeType === 'CONDITION'}<div
								class="rounded-card border border-border p-2"
							>
								<ConditionBuilder {meta} bind:condition={conditionState} /><button
									class="mt-2 rounded-control bg-primary-600 px-2 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
									disabled={!editable}
									onclick={() => patchConfig('condition', builderConditionToJson(conditionState))}
									>Apply condition</button
								>
							</div>
						{:else if Object.keys(selectedNode.data.config).length}<pre
								class="max-h-48 overflow-auto rounded-control bg-surface-sunken p-2 text-[10px] text-text">{JSON.stringify(
									selectedNode.data.config,
									null,
									2
								)}</pre>{/if}
					</div>
				{:else if selectedEdge}
					<div class="space-y-3 text-xs" data-testid="edge-config">
						<div class="flex items-center justify-between">
							<StatusBadge
								value={selectedEdge.label ? `EDGE ${selectedEdge.label}` : 'EDGE'}
							/>{#if editable}<button class="text-danger" onclick={deleteSelectedEdge}
									>Delete edge</button
								>{/if}
						</div>
						<p class="text-text-muted">
							<span class="font-mono">{selectedEdge.source}</span> →
							<span class="font-mono">{selectedEdge.target}</span>
						</p>
					</div>
				{:else}
					<p class="text-xs text-text-muted">Select a node or edge to inspect it.</p>
					{#if !editable && selected}<div
							class="mt-3 rounded-card border border-warning/25 bg-warning-bg p-3 text-[11px] text-warning"
							data-testid="readonly-note"
						>
							This {selected.status} version is immutable. Start a new draft to make changes.
						</div>{/if}
				{/if}
			</div>
		</aside>
	</div>
{:else}
	<p class="mt-3 text-sm text-text-muted">Loading…</p>
{/if}

<style>
	:global(.edge-true .svelte-flow__edge-path) {
		stroke: var(--color-success);
	}
	:global(.edge-false .svelte-flow__edge-path) {
		stroke: var(--color-danger);
	}
	:global(.svelte-flow__edge-text) {
		font-size: 10px;
		font-weight: 700;
	}
</style>
