import { MarkerType, type Connection } from '@xyflow/svelte';
import type { StrategyGraph } from '$lib/api/types';
import type { StrategyFlowEdge, StrategyFlowNode } from './types';

export interface FlowGraph {
	nodes: StrategyFlowNode[];
	edges: StrategyFlowEdge[];
}

function edgeId(source: string, target: string, label: string | null): string {
	return `edge:${source}:${label ?? 'NEXT'}:${target}`;
}

export function graphToFlow(graph: StrategyGraph, readOnly = false): FlowGraph {
	return {
		nodes: graph.nodes.map((node) => ({
			id: node.node_key,
			type: 'strategy',
			position: { ...node.position },
			data: {
				nodeType: node.node_type,
				name: node.name,
				referenceCode: node.reference_code,
				onError: node.on_error,
				config: structuredClone(node.config),
				readOnly
			},
			draggable: !readOnly,
			connectable: !readOnly,
			deletable: !readOnly && node.node_type !== 'START'
		})),
		edges: graph.edges.map((edge) => ({
			id: edgeId(edge.from, edge.to, edge.label),
			type: 'smoothstep',
			source: edge.from,
			target: edge.to,
			sourceHandle: edge.label ?? undefined,
			label: edge.label ?? undefined,
			markerEnd: { type: MarkerType.ArrowClosed },
			animated: false,
			class:
				edge.label === 'TRUE' ? 'edge-true' : edge.label === 'FALSE' ? 'edge-false' : undefined,
			deletable: !readOnly
		}))
	};
}

export function flowToGraph(nodes: StrategyFlowNode[], edges: StrategyFlowEdge[]): StrategyGraph {
	return {
		nodes: nodes.map((node) => ({
			node_key: node.id,
			node_type: node.data.nodeType,
			name: node.data.name,
			reference_code: node.data.referenceCode,
			on_error: node.data.onError,
			config: structuredClone(node.data.config),
			position: {
				x: Math.round(node.position.x),
				y: Math.round(node.position.y)
			}
		})),
		edges: edges.map((edge) => ({
			from: edge.source,
			to: edge.target,
			label: typeof edge.label === 'string' ? edge.label.toUpperCase() : null
		}))
	};
}

export function connectionToEdge(connection: Connection): StrategyFlowEdge {
	const label = connection.sourceHandle?.toUpperCase() ?? null;
	return {
		id: edgeId(connection.source, connection.target, label),
		type: 'smoothstep',
		source: connection.source,
		target: connection.target,
		sourceHandle: connection.sourceHandle ?? undefined,
		targetHandle: connection.targetHandle ?? undefined,
		label: label ?? undefined,
		markerEnd: { type: MarkerType.ArrowClosed },
		class: label === 'TRUE' ? 'edge-true' : label === 'FALSE' ? 'edge-false' : undefined
	};
}

export interface GraphIssue {
	field: string;
	issue: string;
	nodeKey?: string;
	edgeId?: string;
}

export function validateFlowGraph(
	nodes: StrategyFlowNode[],
	edges: StrategyFlowEdge[]
): GraphIssue[] {
	const issues: GraphIssue[] = [];
	const starts = nodes.filter((node) => node.data.nodeType === 'START');
	if (starts.length !== 1)
		issues.push({ field: 'graph.nodes', issue: 'Flow must contain exactly one START node.' });
	if (!nodes.some((node) => node.data.nodeType === 'END')) {
		issues.push({ field: 'graph.nodes', issue: 'Flow must contain at least one END node.' });
	}
	const keys = new Set(nodes.map((node) => node.id));
	for (const node of nodes) {
		if (!node.data.name.trim())
			issues.push({ field: 'name', issue: 'Node name is required.', nodeKey: node.id });
		if (
			['RULE_SET', 'SCORECARD', 'DECISION_TABLE'].includes(node.data.nodeType) &&
			!node.data.referenceCode
		) {
			issues.push({
				field: 'reference_code',
				issue: `${node.data.nodeType} requires a reference.`,
				nodeKey: node.id
			});
		}
		if (node.data.nodeType === 'CONDITION' && !node.data.config.condition) {
			issues.push({
				field: 'config.condition',
				issue: 'CONDITION requires a condition.',
				nodeKey: node.id
			});
		}
	}
	for (const edge of edges) {
		if (!keys.has(edge.source) || !keys.has(edge.target)) {
			issues.push({
				field: 'graph.edges',
				issue: 'Edge references an unknown node.',
				edgeId: edge.id
			});
		}
		if (edge.source === edge.target)
			issues.push({ field: 'graph.edges', issue: 'Self-loop is not allowed.', edgeId: edge.id });
	}
	for (const condition of nodes.filter((node) => node.data.nodeType === 'CONDITION')) {
		for (const label of ['TRUE', 'FALSE']) {
			const matches = edges.filter(
				(edge) => edge.source === condition.id && String(edge.label ?? '').toUpperCase() === label
			);
			if (matches.length !== 1) {
				issues.push({
					field: 'graph.edges',
					issue: `CONDITION must have exactly one ${label} edge.`,
					nodeKey: condition.id
				});
			}
		}
	}
	return issues;
}
