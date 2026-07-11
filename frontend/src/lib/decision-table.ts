export interface DecisionTableCondition {
	field: string;
	operator: string;
	value?: unknown;
}

export interface LimitFromField {
	field: string;
	pct: number;
}

export interface DecisionTableOutput {
	decision: string;
	risk_grade?: string | null;
	reason_code?: string | null;
	approved_limit?: number | null;
	approved_limit_pct_of?: LimitFromField | null;
	approved_tenor_months?: number | null;
	pricing_rate?: number | null;
}

export interface DecisionTableRowConfig {
	priority?: number;
	conditions: DecisionTableCondition[];
	output: DecisionTableOutput;
}

export interface DecisionTableConfig {
	hit_policy?: 'FIRST_MATCH' | 'PRIORITY';
	rows: DecisionTableRowConfig[];
	no_match_decision?: string;
	no_match_reason_code?: string | null;
	above_limit_reason_code?: string | null;
}

export interface GridColumn {
	path: string;
}

export interface GridCell {
	active: boolean;
	operator: string;
	value: unknown;
}

export interface GridRow {
	key: string;
	priority: number;
	cells: Record<string, GridCell>;
	output: DecisionTableOutput;
}

export interface DecisionTableGridState {
	hitPolicy: 'FIRST_MATCH' | 'PRIORITY';
	columns: GridColumn[];
	rows: GridRow[];
	noMatchDecision: string;
	noMatchReasonCode: string;
	aboveLimitReasonCode: string;
}

let nextKey = 0;
const rowKey = () => `row-${++nextKey}`;

export function emptyOutput(): DecisionTableOutput {
	return {
		decision: 'MANUAL_REVIEW',
		risk_grade: null,
		reason_code: null,
		approved_limit: null,
		approved_limit_pct_of: null,
		approved_tenor_months: null,
		pricing_rate: null
	};
}

export function emptyGridRow(columns: GridColumn[], priority = 0): GridRow {
	return {
		key: rowKey(),
		priority,
		cells: Object.fromEntries(
			columns.map((column) => [
				column.path,
				{ active: false, operator: '=', value: '' } satisfies GridCell
			])
		),
		output: emptyOutput()
	};
}

export function configToGrid(config: Record<string, unknown>): DecisionTableGridState {
	const source = config as unknown as DecisionTableConfig;
	const rows = Array.isArray(source.rows) ? source.rows : [];
	const paths: string[] = [];
	for (const row of rows) {
		for (const condition of row.conditions ?? []) {
			if (condition.field && !paths.includes(condition.field)) paths.push(condition.field);
		}
	}
	const columns = paths.map((path) => ({ path }));
	const gridRows = rows.map((row, index) => {
		const conditions = new Map(
			(row.conditions ?? []).map((condition) => [condition.field, condition])
		);
		return {
			key: rowKey(),
			priority: row.priority ?? index + 1,
			cells: Object.fromEntries(
				columns.map((column) => {
					const condition = conditions.get(column.path);
					return [
						column.path,
						condition
							? { active: true, operator: condition.operator, value: condition.value ?? '' }
							: { active: false, operator: '=', value: '' }
					];
				})
			),
			output: { ...emptyOutput(), ...(row.output ?? {}) }
		};
	});
	return {
		hitPolicy: source.hit_policy ?? 'FIRST_MATCH',
		columns,
		rows: gridRows.length ? gridRows : [emptyGridRow(columns, 1)],
		noMatchDecision: source.no_match_decision ?? 'MANUAL_REVIEW',
		noMatchReasonCode: source.no_match_reason_code ?? '',
		aboveLimitReasonCode: source.above_limit_reason_code ?? ''
	};
}

export function gridToConfig(state: DecisionTableGridState): DecisionTableConfig {
	return {
		hit_policy: state.hitPolicy,
		rows: state.rows.map((row, index) => ({
			priority: state.hitPolicy === 'PRIORITY' ? Number(row.priority || index + 1) : 0,
			conditions: state.columns.flatMap((column) => {
				const cell = row.cells[column.path];
				if (!cell?.active) return [];
				return [
					{
						field: column.path,
						operator: cell.operator,
						value: cell.operator === 'exists' || cell.operator === 'is_null' ? null : cell.value
					}
				];
			}),
			output: compactOutput(row.output)
		})),
		no_match_decision: state.noMatchDecision,
		no_match_reason_code: state.noMatchReasonCode || null,
		above_limit_reason_code: state.aboveLimitReasonCode || null
	};
}

function compactOutput(output: DecisionTableOutput): DecisionTableOutput {
	const result: DecisionTableOutput = { decision: output.decision };
	if (output.risk_grade) result.risk_grade = output.risk_grade;
	if (output.reason_code) result.reason_code = output.reason_code;
	if (output.approved_limit !== null && output.approved_limit !== undefined)
		result.approved_limit = Number(output.approved_limit);
	if (output.approved_limit_pct_of?.field && output.approved_limit_pct_of.pct)
		result.approved_limit_pct_of = {
			field: output.approved_limit_pct_of.field,
			pct: Number(output.approved_limit_pct_of.pct)
		};
	if (output.approved_tenor_months !== null && output.approved_tenor_months !== undefined)
		result.approved_tenor_months = Number(output.approved_tenor_months);
	if (output.pricing_rate !== null && output.pricing_rate !== undefined)
		result.pricing_rate = Number(output.pricing_rate);
	return result;
}

export function rowSummary(row: GridRow, columns: GridColumn[]): string {
	const conditions = columns
		.filter((column) => row.cells[column.path]?.active)
		.map((column) => {
			const cell = row.cells[column.path];
			return `${column.path} ${cell.operator} ${String(cell.value ?? '')}`;
		});
	return `${conditions.length ? conditions.join(' AND ') : 'ANY'} → ${row.output.decision}`;
}
