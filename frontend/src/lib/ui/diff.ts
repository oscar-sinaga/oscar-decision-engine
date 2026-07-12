export interface DiffRow {
	field: string;
	before: unknown;
	after: unknown;
	kind: 'added' | 'removed' | 'changed';
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
	return (
		typeof value === 'object' &&
		value !== null &&
		!Array.isArray(value) &&
		Object.getPrototypeOf(value) === Object.prototype
	);
}

export function flattenObject(
	value: Record<string, unknown>,
	prefix = ''
): Record<string, unknown> {
	const result: Record<string, unknown> = {};
	for (const [key, item] of Object.entries(value)) {
		const path = prefix ? `${prefix}.${key}` : key;
		if (isPlainObject(item)) {
			Object.assign(result, flattenObject(item, path));
		} else {
			result[path] = item;
		}
	}
	return result;
}

export function flattenDiff(before: unknown, after: unknown): DiffRow[] | null {
	if (!isPlainObject(before) || !isPlainObject(after)) return null;

	const left = flattenObject(before);
	const right = flattenObject(after);
	const keys = [...new Set([...Object.keys(left), ...Object.keys(right)])].sort();
	const rows: DiffRow[] = [];

	for (const field of keys) {
		const hasBefore = Object.hasOwn(left, field);
		const hasAfter = Object.hasOwn(right, field);

		if (!hasBefore) {
			rows.push({ field, before: undefined, after: right[field], kind: 'added' });
			continue;
		}
		if (!hasAfter) {
			rows.push({ field, before: left[field], after: undefined, kind: 'removed' });
			continue;
		}
		if (JSON.stringify(left[field]) !== JSON.stringify(right[field])) {
			rows.push({ field, before: left[field], after: right[field], kind: 'changed' });
		}
	}

	return rows;
}
