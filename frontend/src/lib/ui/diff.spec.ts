import { describe, expect, test } from 'vitest';
import { flattenDiff, flattenObject } from './diff';
describe('diff utilities', () => {
	test('flattens nested plain objects', () =>
		expect(flattenObject({ a: { b: 1 }, c: 'x' })).toEqual({ 'a.b': 1, c: 'x' }));
	test('returns added removed and changed rows', () =>
		expect(flattenDiff({ a: 1, b: 2 }, { a: 3, c: 4 })).toEqual([
			{ field: 'a', before: 1, after: 3, kind: 'changed' },
			{ field: 'b', before: 2, after: undefined, kind: 'removed' },
			{ field: 'c', before: undefined, after: 4, kind: 'added' }
		]));
	test('falls back for non objects', () => expect(flattenDiff([], {})).toBeNull());
});
