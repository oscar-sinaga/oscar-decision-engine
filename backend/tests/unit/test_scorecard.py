from app.engine.scorecard import parse_scorecard_config, resolve_score

CONFIG = parse_scorecard_config(
    {
        "score_field": "model_outputs.credit_score",
        "model_version_field": "model_outputs.model_version",
        "bands": [
            {"min_score": 750, "risk_grade": "A"},
            {"min_score": 650, "risk_grade": "B"},
            {"min_score": 550, "risk_grade": "C"},
        ],
        "below_bands_risk_grade": "E",
        "missing_score_decision": "MANUAL_REVIEW",
        "missing_score_reason_code": "SCORE_UNAVAILABLE",
    }
)


def test_score_maps_to_band() -> None:
    outcome = resolve_score(
        CONFIG,
        {"model_outputs.credit_score": 684, "model_outputs.model_version": "MOTOR_SCORE_V1"},
    )
    assert outcome.risk_grade == "B"
    assert outcome.score == 684
    assert outcome.model_version == "MOTOR_SCORE_V1"
    assert outcome.score_missing is False


def test_boundary_is_inclusive() -> None:
    assert resolve_score(CONFIG, {"model_outputs.credit_score": 750}).risk_grade == "A"
    assert resolve_score(CONFIG, {"model_outputs.credit_score": 749.9}).risk_grade == "B"


def test_below_all_bands() -> None:
    assert resolve_score(CONFIG, {"model_outputs.credit_score": 300}).risk_grade == "E"


def test_missing_or_invalid_score() -> None:
    assert resolve_score(CONFIG, {}).score_missing is True
    assert resolve_score(CONFIG, {"model_outputs.credit_score": "high"}).score_missing is True
    assert resolve_score(CONFIG, {"model_outputs.credit_score": True}).score_missing is True
