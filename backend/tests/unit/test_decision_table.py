from app.engine.decision_table import (
    evaluate_decision_table,
    find_overlapping_rows,
    parse_decision_table_config,
)


def _config(hit_policy: str = "FIRST_MATCH") -> dict[str, object]:
    return {
        "hit_policy": hit_policy,
        "no_match_decision": "MANUAL_REVIEW",
        "no_match_reason_code": "NO_MATCHING_DECISION_ROW",
        "rows": [
            {
                "priority": 2,
                "conditions": [{"field": "score.risk_grade", "operator": "=", "value": "B"}],
                "output": {"decision": "APPROVE", "approved_tenor_months": 18},
            },
            {
                "priority": 1,
                "conditions": [
                    {"field": "score.risk_grade", "operator": "in", "value": ["A", "B"]}
                ],
                "output": {"decision": "APPROVE", "approved_tenor_months": 24},
            },
        ],
    }


def test_first_match_uses_listed_order() -> None:
    config = parse_decision_table_config(_config("FIRST_MATCH"))
    result = evaluate_decision_table(config, {"score.risk_grade": "B"})
    assert result.matched and result.row_index == 0
    assert result.output.approved_tenor_months == 18


def test_priority_policy_orders_by_priority() -> None:
    config = parse_decision_table_config(_config("PRIORITY"))
    result = evaluate_decision_table(config, {"score.risk_grade": "B"})
    assert result.matched and result.row_index == 1
    assert result.output.approved_tenor_months == 24


def test_no_match_falls_back_conservatively() -> None:
    config = parse_decision_table_config(_config())
    result = evaluate_decision_table(config, {"score.risk_grade": "E"})
    assert result.matched is False
    assert result.output.decision.value == "MANUAL_REVIEW"
    assert result.output.reason_code == "NO_MATCHING_DECISION_ROW"
    assert len(result.row_details) == 2  # every row evaluation is recorded


def test_overlap_detection_flags_ambiguous_rows() -> None:
    config = parse_decision_table_config(_config())
    # Grade "B" satisfies both rows.
    assert (0, 1) in find_overlapping_rows(config)


def test_overlap_detection_accepts_disjoint_ranges() -> None:
    config = parse_decision_table_config(
        {
            "rows": [
                {
                    "conditions": [{"field": "affordability.dti", "operator": "<=", "value": 0.35}],
                    "output": {"decision": "APPROVE"},
                },
                {
                    "conditions": [{"field": "affordability.dti", "operator": ">", "value": 0.35}],
                    "output": {"decision": "MANUAL_REVIEW", "reason_code": "X"},
                },
            ]
        }
    )
    assert find_overlapping_rows(config) == []
