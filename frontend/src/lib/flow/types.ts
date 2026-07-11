import type { Edge, Node } from '@xyflow/svelte';
import type { StrategyGraphNode } from '$lib/api/types';

export interface StrategyNodeData extends Record<string, unknown> {
	nodeType: string;
	name: string;
	referenceCode: string | null;
	onError: string;
	config: Record<string, unknown>;
	invalid?: boolean;
	readOnly?: boolean;
}

export type StrategyFlowNode = Node<StrategyNodeData, 'strategy'>;
export type StrategyFlowEdge = Edge<Record<string, unknown>, 'smoothstep'>;

export const EDITABLE_NODE_TYPES = [
	'VALIDATION',
	'CALCULATION',
	'RULE_SET',
	'SCORECARD',
	'DECISION_TABLE',
	'CONDITION',
	'END'
] as const;

export function defaultGraphNode(
	nodeType: string,
	nodeKey: string,
	position: { x: number; y: number }
): StrategyGraphNode {
	return {
		node_key: nodeKey,
		node_type: nodeType,
		name:
			nodeType === 'START' ? 'Start' : nodeType === 'END' ? 'End' : nodeType.replaceAll('_', ' '),
		reference_code: null,
		on_error: 'FAIL',
		config:
			nodeType === 'CONDITION'
				? { condition: { all: [{ field: '', operator: '=', value: '' }] } }
				: {},
		position
	};
}
