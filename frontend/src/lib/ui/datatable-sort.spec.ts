import { describe, expect, test } from 'vitest';
import { nextSortState, sortRows } from './datatable-sort';
const rows = [
	{ id: 'b', count: 2 },
	{ id: 'a', count: 10 }
];
describe('DataTable sorting', () => {
	test('sorts strings ascending', () =>
		expect(sortRows(rows, { key: 'id', direction: 'asc' }).map((r) => r.id)).toEqual(['a', 'b']));
	test('sorts numbers descending', () =>
		expect(sortRows(rows, { key: 'count', direction: 'desc' }).map((r) => r.count)).toEqual([
			10, 2
		]));
	test('toggles direction', () =>
		expect(nextSortState({ key: 'id', direction: 'asc' }, 'id')).toEqual({
			key: 'id',
			direction: 'desc'
		}));
});
