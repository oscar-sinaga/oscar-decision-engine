export type BuilderCondition = BuilderLeaf | BuilderGroup;

export interface BuilderLeaf {
	kind: 'condition';
	field: string;
	operator: string;
	value?: unknown;
	negated: boolean;
}

export interface BuilderGroup {
	kind: 'group';
	logic: 'all' | 'any';
	children: BuilderCondition[];
	negated: boolean;
}

export interface BuilderAction {
	type: string;
	decision?: string;
	reason_code?: string;
	target?: string;
	value?: unknown;
	expression?: string;
}

export interface BuilderBranch {
	when: BuilderCondition;
	then: BuilderAction[];
}

export interface BuilderState {
	form: 'legacy' | 'branched';
	ruleKind: string;
	branches: BuilderBranch[];
	defaultActions: BuilderAction[] | null;
}

type JsonObject = Record<string, unknown>;

function object(value: unknown): JsonObject | null {
	return typeof value === 'object' && value !== null && !Array.isArray(value)
		? (value as JsonObject)
		: null;
}

function parseCondition(value: unknown, depth = 0): BuilderCondition | null {
	if (depth > 20) return null;
	const node = object(value);
	if (!node) return null;
	if ('not' in node) {
		const child = parseCondition(node.not, depth + 1);
		return child ? { ...child, negated: !child.negated } : null;
	}
	for (const logic of ['all', 'any'] as const) {
		if (logic in node) {
			if (!Array.isArray(node[logic]) || node[logic].length === 0) return null;
			const children = node[logic].map((child) => parseCondition(child, depth + 1));
			if (children.some((child) => child === null)) return null;
			return {
				kind: 'group',
				logic,
				children: children as BuilderCondition[],
				negated: false
			};
		}
	}
	if (typeof node.field !== 'string' || typeof node.operator !== 'string') return null;
	return {
		kind: 'condition',
		field: node.field,
		operator: node.operator,
		...('value' in node ? { value: node.value } : {}),
		negated: false
	};
}

function parseActions(value: unknown): BuilderAction[] | null {
	if (!Array.isArray(value) || value.length === 0) return null;
	const actions: BuilderAction[] = [];
	for (const raw of value) {
		const action = object(raw);
		if (!action) return null;
		const type = typeof action.type === 'string' ? action.type : 'SET_DECISION';
		actions.push({
			type: type === 'SET_ATTRIBUTE' ? 'SET_OUTPUT' : type,
			...(typeof action.decision === 'string' ? { decision: action.decision } : {}),
			...(typeof action.reason_code === 'string' ? { reason_code: action.reason_code } : {}),
			...(typeof action.target === 'string'
				? { target: action.target }
				: typeof action.attribute === 'string'
					? { target: action.attribute }
					: {}),
			...(typeof action.expression === 'string' ? { expression: action.expression } : {}),
			...('value' in action
				? { value: action.value }
				: 'attribute_value' in action
					? { value: action.attribute_value }
					: {})
		});
	}
	return actions;
}

export function jsonToBuilder(definition: unknown): {
	state: BuilderState | null;
	supported: boolean;
} {
	const root = object(definition);
	if (!root || 'expression' in root || 'expression_ast' in root) {
		return { state: null, supported: false };
	}
	const ruleKind = typeof root.rule_kind === 'string' ? root.rule_kind : 'POLICY_OUTCOME';
	if ('condition' in root || 'action' in root) {
		const when = parseCondition(root.condition);
		const then = parseActions(root.action ? [root.action] : null);
		if (!when || !then) return { state: null, supported: false };
		return {
			state: { form: 'legacy', ruleKind, branches: [{ when, then }], defaultActions: null },
			supported: true
		};
	}
	if (!Array.isArray(root.branches) || root.branches.length === 0) {
		return { state: null, supported: false };
	}
	const branches: BuilderBranch[] = [];
	for (const raw of root.branches) {
		const branch = object(raw);
		const when = parseCondition(branch?.when);
		const then = parseActions(branch?.then);
		if (!when || !then) return { state: null, supported: false };
		branches.push({ when, then });
	}
	const defaultActions = root.default == null ? null : parseActions(root.default);
	if (root.default != null && !defaultActions) return { state: null, supported: false };
	return {
		state: { form: 'branched', ruleKind, branches, defaultActions },
		supported: true
	};
}

function conditionToJson(condition: BuilderCondition): JsonObject {
	let value: JsonObject;
	if (condition.kind === 'condition') {
		value = {
			field: condition.field,
			operator: condition.operator,
			...(condition.value !== undefined ? { value: condition.value } : {})
		};
	} else {
		value = { [condition.logic]: condition.children.map(conditionToJson) };
	}
	return condition.negated ? { not: value } : value;
}

export function builderConditionToJson(condition: BuilderCondition): JsonObject {
	return conditionToJson(condition);
}

function actionToJson(action: BuilderAction): JsonObject {
	return {
		type: action.type,
		...(action.decision ? { decision: action.decision } : {}),
		...(action.reason_code ? { reason_code: action.reason_code } : {}),
		...(action.target ? { target: action.target } : {}),
		...(action.expression
			? { expression: action.expression }
			: action.value !== undefined
				? { value: action.value }
				: {})
	};
}

export function builderToJson(state: BuilderState): JsonObject {
	if (state.form === 'legacy') {
		const branch = state.branches[0];
		return {
			rule_kind: state.ruleKind,
			condition: conditionToJson(branch.when),
			action: actionToJson(branch.then[0])
		};
	}
	return {
		rule_kind: state.ruleKind,
		branches: state.branches.map((branch) => ({
			when: conditionToJson(branch.when),
			then: branch.then.map(actionToJson)
		})),
		...(state.defaultActions
			? { default: state.defaultActions.map(actionToJson) }
			: { default: null })
	};
}

function conditionText(condition: BuilderCondition): string {
	const text =
		condition.kind === 'condition'
			? `${condition.field} ${condition.operator}${condition.value === undefined ? '' : ` ${JSON.stringify(condition.value)}`}`
			: `(${condition.children.map(conditionText).join(condition.logic === 'all' ? ' AND ' : ' OR ')})`;
	return condition.negated ? `NOT ${text}` : text;
}

function actionText(action: BuilderAction): string {
	if (action.type === 'SET_OUTPUT')
		return `${action.target ?? 'output'} = ${action.expression ?? JSON.stringify(action.value)}`;
	if (action.type === 'SET_DECISION') return action.decision ?? 'decision';
	return [action.type, action.reason_code].filter(Boolean).join(' ');
}

export function humanPreview(state: BuilderState): string {
	const lines = state.branches.map(
		(branch) => `WHEN ${conditionText(branch.when)} → ${branch.then.map(actionText).join(', ')}`
	);
	if (state.defaultActions) {
		lines.push(`ELSE → ${state.defaultActions.map(actionText).join(', ')}`);
	}
	return lines.join('\n');
}

function sqlLiteral(value: unknown): string {
	if (value === null || value === undefined) return 'NULL';
	if (value === true) return 'TRUE';
	if (value === false) return 'FALSE';
	if (typeof value === 'string') return `'${value.replaceAll("'", "''")}'`;
	if (Array.isArray(value)) return `(${value.map(sqlLiteral).join(', ')})`;
	return String(value);
}

function conditionSql(condition: BuilderCondition): string {
	let text: string;
	if (condition.kind === 'condition') {
		if (condition.operator === 'exists') text = `${condition.field} IS NOT NULL`;
		else if (condition.operator === 'is_null') text = `${condition.field} IS NULL`;
		else if (condition.operator === 'in')
			text = `${condition.field} IN ${sqlLiteral(condition.value)}`;
		else if (condition.operator === 'not_in')
			text = `${condition.field} NOT IN ${sqlLiteral(condition.value)}`;
		else text = `${condition.field} ${condition.operator} ${sqlLiteral(condition.value)}`;
	} else {
		text = `(${condition.children.map(conditionSql).join(condition.logic === 'all' ? ' AND ' : ' OR ')})`;
	}
	return condition.negated ? `(NOT ${text})` : text;
}

function outputOnly(actions: BuilderAction[]): BuilderAction | null {
	return actions.length === 1 && actions[0].type === 'SET_OUTPUT' && actions[0].target
		? actions[0]
		: null;
}

function actionSqlValue(action: BuilderAction): string {
	return action.expression ?? sqlLiteral(action.value);
}

function actionComment(action: BuilderAction): string {
	return [
		action.type,
		action.decision,
		action.target,
		action.reason_code ? `(${action.reason_code})` : ''
	]
		.filter(Boolean)
		.join(' ');
}

export function sqlPreview(state: BuilderState): string {
	const outputs = state.branches.map((branch) => outputOnly(branch.then));
	const fallback = state.defaultActions ? outputOnly(state.defaultActions) : null;
	const targets = new Set(outputs.filter(Boolean).map((action) => action!.target));
	if (fallback) targets.add(fallback.target);
	if (outputs.every(Boolean) && targets.size === 1) {
		const target = [...targets][0];
		const lines = ['CASE'];
		state.branches.forEach((branch, index) => {
			lines.push(`  WHEN ${conditionSql(branch.when)} THEN ${actionSqlValue(outputs[index]!)}`);
		});
		if (fallback) lines.push(`  ELSE ${actionSqlValue(fallback)}`);
		lines.push(`END  -- writes ${target}`);
		return lines.join('\n');
	}
	const lines: string[] = [];
	state.branches.forEach((branch, index) => {
		lines.push(`${index === 0 ? 'WHEN' : 'ELSE WHEN'} ${conditionSql(branch.when)}`);
		branch.then.forEach((action) => lines.push(`  -- ${actionComment(action)}`));
	});
	if (state.defaultActions) {
		lines.push('ELSE');
		state.defaultActions.forEach((action) => lines.push(`  -- ${actionComment(action)}`));
	}
	return lines.join('\n');
}

export function expressionSqlPreview(expression: string, outputTarget: string): string {
	return `${expression}\n-- writes ${outputTarget}`;
}
