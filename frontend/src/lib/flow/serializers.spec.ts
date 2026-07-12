import { describe, expect, it } from 'vitest';
import type { StrategyGraph } from '$lib/api/types';
import { autoLayout } from './layout';
import { flowToGraph, graphToFlow, validateFlowGraph } from './serializers';

const graph: StrategyGraph = {
	nodes: [
		{
			node_key: 'start',
			node_type: 'START',
			name: 'Start',
			reference_code: null,
			on_error: 'FAIL',
			config: {},
			position: { x: 0, y: 10 }
		},
		{
			node_key: 'condition',
			node_type: 'CONDITION',
			name: 'Adult?',
			reference_code: null,
			on_error: 'FAIL',
			config: { condition: { field: 'applicant.age', operator: '>=', value: 18 } },
			position: { x: 250, y: 10 }
		},
		{
			node_key: 'end-true',
			node_type: 'END',
			name: 'Approve end',
			reference_code: null,
			on_error: 'FAIL',
			config: {},
			position: { x: 500, y: 0 }
		},
		{
			node_key: 'end-false',
			node_type: 'END',
			name: 'Review end',
			reference_code: null,
			on_error: 'FAIL',
			config: {},
			position: { x: 500, y: 150 }
		}
	],
	edges: [
		{ from: 'start', to: 'condition', label: null },
		{ from: 'condition', to: 'end-true', label: 'TRUE' },
		{ from: 'condition', to: 'end-false', label: 'FALSE' }
	]
};

describe('strategy graph serializers', () => {
	it('round-trips graph data and positions', () => {
		const flow = graphToFlow(graph);
		expect(flowToGraph(flow.nodes, flow.edges)).toEqual(graph);
	});

	it('marks read-only nodes as non-draggable and non-connectable', () => {
		const flow = graphToFlow(graph, true);
		expect(flow.nodes.every((node) => node.draggable === false && node.connectable === false)).toBe(
			true
		);
	});

	it('validates condition branch cardinality', () => {
		const flow = graphToFlow({
			...graph,
			edges: graph.edges.filter((edge) => edge.label !== 'FALSE')
		});
		expect(validateFlowGraph(flow.nodes, flow.edges).map((issue) => issue.issue)).toContain(
			'CONDITION must have exactly one FALSE edge.'
		);
	});

	it('tolerates a missing graph', () => {
		expect(graphToFlow(null)).toEqual({ nodes: [], edges: [] });
		expect(graphToFlow(undefined)).toEqual({ nodes: [], edges: [] });
	});

	it('clones proxied configs without structuredClone (Svelte 5 reactive state)', () => {
		const proxiedConfig = new Proxy(
			{ condition: { field: 'applicant.age', operator: '>=', value: 18 } },
			{}
		);
		expect(() => structuredClone(proxiedConfig)).toThrow();
		const flow = graphToFlow({
			nodes: [{ ...graph.nodes[1], config: proxiedConfig }],
			edges: []
		});
		const condition = flow.nodes.find((node) => node.id === 'condition')!;
		expect(condition.data.config).toEqual(graph.nodes[1].config);
		expect(condition.data.config).not.toBe(proxiedConfig);
	});

	it('fills empty node names with a readable default', () => {
		const flow = graphToFlow({
			nodes: [{ ...graph.nodes[0], name: '' }],
			edges: []
		});
		expect(flow.nodes[0].data.name).toBe('Start');
	});

	it('lays out layers left-to-right', () => {
		const flow = graphToFlow(graph);
		const laidOut = autoLayout(flow.nodes, flow.edges);
		const start = laidOut.find((node) => node.id === 'start')!;
		const condition = laidOut.find((node) => node.id === 'condition')!;
		expect(condition.position.x).toBeGreaterThan(start.position.x);
	});
});
