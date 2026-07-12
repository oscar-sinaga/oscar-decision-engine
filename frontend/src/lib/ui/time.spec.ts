import { describe, expect, test } from 'vitest';
import { formatRelativeTime } from './time';
const now = Date.parse('2026-07-12T12:00:00Z');
describe('formatRelativeTime', () => {
	test('formats minutes', () =>
		expect(formatRelativeTime('2026-07-12T11:57:00Z', now)).toBe('3m ago'));
	test('formats hours', () =>
		expect(formatRelativeTime('2026-07-12T10:00:00Z', now)).toBe('2h ago'));
	test('formats days', () =>
		expect(formatRelativeTime('2026-07-10T12:00:00Z', now)).toBe('2d ago'));
});
