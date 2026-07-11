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

describe('SQL-style preview parity fixtures', () => {
	it('renders output branches as CASE', async () => {
		const { sqlPreview } = await import('./rule-format');
		const source = {
			rule_kind: 'CLASSIFICATION',
			branches: [
				{
					when: { all: [{ field: 'loan.ltv', operator: '>', value: 0.85 }] },
					then: [{ type: 'SET_OUTPUT', target: 'outputs.risk', value: 'HIGH' }]
				},
				{
					when: { all: [{ field: 'loan.ltv', operator: '>', value: 0.7 }] },
					then: [{ type: 'SET_OUTPUT', target: 'outputs.risk', value: 'MEDIUM' }]
				}
			],
			default: [{ type: 'SET_OUTPUT', target: 'outputs.risk', value: 'LOW' }]
		};
		const state = jsonToBuilder(source).state!;
		expect(sqlPreview(state)).toBe(
			"CASE\n  WHEN (loan.ltv > 0.85) THEN 'HIGH'\n  WHEN (loan.ltv > 0.7) THEN 'MEDIUM'\n  ELSE 'LOW'\nEND  -- writes outputs.risk"
		);
	});

	it('renders nested conditions and decision comments', async () => {
		const { sqlPreview } = await import('./rule-format');
		const source = {
			rule_kind: 'POLICY_OUTCOME',
			branches: [
				{
					when: {
						all: [
							{ field: 'loan.ltv', operator: '>=', value: 0.9 },
							{ not: { field: 'fraud.hit', operator: '=', value: true } }
						]
					},
					then: [{ type: 'SET_DECISION', decision: 'REJECT', reason_code: 'HIGH_LTV' }]
				}
			]
		};
		const preview = sqlPreview(jsonToBuilder(source).state!);
		expect(preview).toContain('loan.ltv >= 0.9');
		expect(preview).toContain('NOT fraud.hit = TRUE');
		expect(preview).toContain('-- SET_DECISION REJECT (HIGH_LTV)');
	});

	it('renders expression rules without parsing as SQL', async () => {
		const { expressionSqlPreview } = await import('./rule-format');
		expect(expressionSqlPreview('monthly_income * 0.3', 'outputs.limit')).toBe(
			'monthly_income * 0.3\n-- writes outputs.limit'
		);
	});

	it('renders SET_OUTPUT.expression as the CASE value', async () => {
		const { sqlPreview } = await import('./rule-format');
		const source = {
			rule_kind: 'STATEMENT',
			branches: [
				{
					when: { all: [{ field: 'flag.active', operator: '=', value: true }] },
					then: [
						{
							type: 'SET_OUTPUT',
							target: 'outputs.limit',
							expression: 'income * 0.3'
						}
					]
				}
			]
		};
		expect(sqlPreview(jsonToBuilder(source).state!)).toContain('THEN income * 0.3');
	});

	it('renders membership and null operators', async () => {
		const { sqlPreview } = await import('./rule-format');
		const source = {
			rule_kind: 'POLICY_OUTCOME',
			branches: [
				{
					when: {
						any: [
							{ field: 'vehicle.type', operator: 'in', value: ['MOTOR', 'CAR'] },
							{ field: 'bureau.score', operator: 'is_null' }
						]
					},
					then: [{ type: 'CONTINUE' }]
				}
			]
		};
		const preview = sqlPreview(jsonToBuilder(source).state!);
		expect(preview).toContain("vehicle.type IN ('MOTOR', 'CAR')");
		expect(preview).toContain('bureau.score IS NULL');
	});
});
