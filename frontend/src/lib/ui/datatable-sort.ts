export type SortDirection = 'asc' | 'desc';
export interface SortState {
	key: string;
	direction: SortDirection;
}

function compareValues(a: unknown, b: unknown): number {
	if (a === b) return 0;
	if (a === null || a === undefined) return 1;
	if (b === null || b === undefined) return -1;
	if (typeof a === 'number' && typeof b === 'number') return a - b;
	if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b);
	const aDate = typeof a === 'string' ? Date.parse(a) : Number.NaN;
	const bDate = typeof b === 'string' ? Date.parse(b) : Number.NaN;
	if (!Number.isNaN(aDate) && !Number.isNaN(bDate) && /[-T:]/.test(String(a))) return aDate - bDate;
	return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

export function sortRows<T extends Record<string, unknown>>(
	rows: T[],
	state: SortState | null
): T[] {
	if (!state) return [...rows];
	const multiplier = state.direction === 'asc' ? 1 : -1;
	return [...rows].sort((a, b) => compareValues(a[state.key], b[state.key]) * multiplier);
}

export function nextSortState(current: SortState | null, key: string): SortState {
	return current?.key === key
		? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
		: { key, direction: 'asc' };
}
