import { describe, expect, it } from 'vitest';

import { builderToJson, humanPreview, jsonToBuilder } from './rule-format';

describe('rule format conversion', () => {
	it('round-trips a legacy rule', () => {
		const source = {
			rule_kind: 'POLICY_OUTCOME',
			condition: { all: [{ field: 'loan.ltv', operator: '>', value: 0.85 }] },
			action: { type: 'SET_DECISION', decision: 'REJECT', reason_code: 'HIGH_LTV' }
		};
		const parsed = jsonToBuilder(source);
		expect(parsed.supported).toBe(true);
		expect(builderToJson(parsed.state!)).toEqual(source);
	});

	it('round-trips nested branches and else', () => {
		const source = {
			rule_kind: 'CLASSIFICATION',
			branches: [
				{
					when: {
						all: [
							{ field: 'loan.ltv', operator: '>', value: 0.8 },
							{ not: { any: [{ field: 'fraud.blacklist_hit', operator: '=', value: true }] } }
						]
					},
					then: [{ type: 'SET_OUTPUT', target: 'outputs.collateral_risk', value: 'HIGH' }]
				}
			],
			default: [{ type: 'SET_OUTPUT', target: 'outputs.collateral_risk', value: 'LOW' }]
		};
		const parsed = jsonToBuilder(source);
		expect(parsed.supported).toBe(true);
		expect(builderToJson(parsed.state!)).toEqual(source);
		expect(humanPreview(parsed.state!)).toContain('ELSE');
	});

	it('flags unsupported expression and malformed shapes', () => {
		expect(jsonToBuilder({ expression_ast: { type: 'literal' } }).supported).toBe(false);
		expect(jsonToBuilder({ branches: [] }).supported).toBe(false);
	});
});
