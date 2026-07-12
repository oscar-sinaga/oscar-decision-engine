import { describe, expect, test } from 'vitest';
import { resolveStatus, STATUS_MAP } from './status';
describe('status map', () => {
	test('maps representative lifecycle, decision, and severity values', () => {
		for (const value of [
			'ACTIVE',
			'APPROVE',
			'PENDING_APPROVAL',
			'MANUAL_REVIEW',
			'REJECT',
			'ERROR',
			'DRAFT',
			'NEW',
			'FRAUD_INVESTIGATION',
			'ESCALATED',
			'RETIRED',
			'SKIP'
		])
			expect(STATUS_MAP[value]).toBeDefined();
	});
	test('unknown values stay safe and neutral', () => {
		expect(resolveStatus('CUSTOM_STATE')).toMatchObject({ label: 'CUSTOM STATE', tone: 'neutral' });
	});
});
