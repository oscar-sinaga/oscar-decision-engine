import type { StrategyFlowEdge, StrategyFlowNode } from './types';

const COLUMN_GAP = 260;
const ROW_GAP = 150;

export function autoLayout(
	nodes: StrategyFlowNode[],
	edges: StrategyFlowEdge[]
): StrategyFlowNode[] {
	if (nodes.length === 0) return [];
	const outgoing = new Map<string, string[]>();
	const incoming = new Map<string, number>();
	for (const node of nodes) {
		outgoing.set(node.id, []);
		incoming.set(node.id, 0);
	}
	for (const edge of edges) {
		outgoing.get(edge.source)?.push(edge.target);
		incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
	}
	const start = nodes.find((node) => node.data.nodeType === 'START') ?? nodes[0];
	const depth = new Map<string, number>([[start.id, 0]]);
	const queue = [start.id];
	while (queue.length) {
		const source = queue.shift()!;
		const nextDepth = (depth.get(source) ?? 0) + 1;
		for (const target of outgoing.get(source) ?? []) {
			if (!depth.has(target) || nextDepth > (depth.get(target) ?? 0)) {
				depth.set(target, nextDepth);
				queue.push(target);
			}
		}
	}
	let fallback = Math.max(0, ...depth.values()) + 1;
	for (const node of nodes) if (!depth.has(node.id)) depth.set(node.id, fallback++);
	const rows = new Map<number, string[]>();
	for (const node of nodes) {
		const level = depth.get(node.id) ?? 0;
		rows.set(level, [...(rows.get(level) ?? []), node.id]);
	}
	return nodes.map((node) => {
		const level = depth.get(node.id) ?? 0;
		const row = rows.get(level) ?? [node.id];
		const index = row.indexOf(node.id);
		return { ...node, position: { x: level * COLUMN_GAP, y: index * ROW_GAP + 40 } };
	});
}
