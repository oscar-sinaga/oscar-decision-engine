"""Scorecard/model score-band resolution (docs/02 §6.5).

MVP mode: the score arrives in the payload (``model_outputs.credit_score``);
the scorecard config maps it to a risk grade. A model-service adapter can
replace the payload source later without changing this mapping logic.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.shared.domain.enums import DecisionType


class ScoreBand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_score: float
    risk_grade: str = Field(min_length=1, max_length=5)


class ScorecardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score_field: str = "model_outputs.credit_score"
    model_version_field: str = "model_outputs.model_version"
    bands: list[ScoreBand] = Field(min_length=1)
    # Risk grade when the score is below every band's min_score.
    below_bands_risk_grade: str = "E"
    missing_score_decision: DecisionType | None = DecisionType.MANUAL_REVIEW
    missing_score_reason_code: str | None = None


class ScoreOutcome(BaseModel):
    score: float | None
    risk_grade: str | None
    model_version: str | None
    score_missing: bool


def parse_scorecard_config(config_json: dict[str, Any]) -> ScorecardConfig:
    return ScorecardConfig.model_validate(config_json)


def resolve_score(config: ScorecardConfig, features: dict[str, Any]) -> ScoreOutcome:
    raw_score = features.get(config.score_field)
    raw_version = features.get(config.model_version_field)
    model_version = str(raw_version) if raw_version is not None else None

    if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
        return ScoreOutcome(
            score=None, risk_grade=None, model_version=model_version, score_missing=True
        )

    score = float(raw_score)
    for band in sorted(config.bands, key=lambda b: b.min_score, reverse=True):
        if score >= band.min_score:
            return ScoreOutcome(
                score=score,
                risk_grade=band.risk_grade,
                model_version=model_version,
                score_missing=False,
            )
    return ScoreOutcome(
        score=score,
        risk_grade=config.below_bands_risk_grade,
        model_version=model_version,
        score_missing=False,
    )
