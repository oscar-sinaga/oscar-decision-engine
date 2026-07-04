import { describe, expect, it } from 'vitest';
import {
	decisionBadgeClass,
	formatCurrency,
	formatDateTime,
	formatPercent,
	statusBadgeClass
} from './format';

describe('formatCurrency', () => {
	it('formats IDR without decimals', () => {
		expect(formatCurrency(12600000)).toContain('12.600.000');
	});
	it('renders a dash for missing values', () => {
		expect(formatCurrency(null)).toBe('—');
		expect(formatCurrency(undefined)).toBe('—');
	});
});

describe('formatPercent', () => {
	it('formats ratios as percentages', () => {
		expect(formatPercent(0.42)).toBe('42.0%');
		expect(formatPercent(0.025, 2)).toBe('2.50%');
	});
	it('renders a dash for missing values', () => {
		expect(formatPercent(null)).toBe('—');
	});
});

describe('formatDateTime', () => {
	it('renders a dash for empty values', () => {
		expect(formatDateTime(null)).toBe('—');
		expect(formatDateTime('')).toBe('—');
	});
	it('passes through unparseable values', () => {
		expect(formatDateTime('not-a-date')).toBe('not-a-date');
	});
});

describe('badge classes', () => {
	it('maps decisions to distinct colors', () => {
		expect(decisionBadgeClass('APPROVE')).toContain('emerald');
		expect(decisionBadgeClass('REJECT')).toContain('red');
		expect(decisionBadgeClass('MANUAL_REVIEW')).toContain('amber');
		expect(decisionBadgeClass('FRAUD_INVESTIGATION')).toContain('purple');
	});
	it('maps lifecycle statuses', () => {
		expect(statusBadgeClass('ACTIVE')).toContain('emerald');
		expect(statusBadgeClass('DRAFT')).toContain('sky');
		expect(statusBadgeClass('PENDING_APPROVAL')).toContain('amber');
		expect(statusBadgeClass('RETIRED')).toContain('slate');
	});
});
