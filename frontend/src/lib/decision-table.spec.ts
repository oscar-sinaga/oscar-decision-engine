import { describe, expect, it } from 'vitest';

import { configToGrid, gridToConfig, rowSummary } from './decision-table';

describe('decision table grid conversion', () => {
	it('round-trips typed conditions and outputs', () => {
		const source = {
			hit_policy: 'PRIORITY',
			rows: [
				{
					priority: 2,
					conditions: [
						{ field: 'outputs.collateral_risk', operator: '=', value: 'HIGH' },
						{ field: 'fraud.blacklist_hit', operator: '=', value: false }
					],
					output: {
						decision: 'MANUAL_REVIEW',
						risk_grade: 'C2',
						reason_code: 'RISK_GRADE_BORDERLINE'
					}
				}
			],
			no_match_decision: 'REJECT'
		};
		expect(gridToConfig(configToGrid(source))).toEqual({
			...source,
			no_match_reason_code: null,
			above_limit_reason_code: null
		});
	});

	it('omits wildcard cells while preserving zero and false values', () => {
		const state = configToGrid({
			rows: [
				{
					conditions: [
						{ field: 'loan.ltv', operator: '>=', value: 0 },
						{ field: 'fraud.blacklist_hit', operator: '=', value: false }
					],
					output: { decision: 'APPROVE' }
				},
				{ conditions: [], output: { decision: 'MANUAL_REVIEW' } }
			]
		});
		const result = gridToConfig(state);
		expect(result.rows[0].conditions).toHaveLength(2);
		expect(result.rows[1].conditions).toEqual([]);
		expect(rowSummary(state.rows[1], state.columns)).toContain('ANY');
	});

	it('preserves percent-of-field limit formulas', () => {
		const source = {
			rows: [
				{
					conditions: [],
					output: {
						decision: 'APPROVE',
						approved_limit_pct_of: { field: 'vehicle.appraisal_value', pct: 0.7 }
					}
				}
			]
		};
		expect(gridToConfig(configToGrid(source)).rows[0].output.approved_limit_pct_of).toEqual(
			source.rows[0].output.approved_limit_pct_of
		);
	});
});
