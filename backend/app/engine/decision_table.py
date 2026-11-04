"""Decision table evaluation (docs/02 §6.4).

A table version's ``config_json`` is parsed into :class:`DecisionTableConfig`.
Rows hold leaf conditions (implicitly ANDed) and one output. Hit policies:

- ``FIRST_MATCH``: rows evaluated in listed order, first matching row wins;
- ``PRIORITY``: rows evaluated in ascending ``priority`` (lower wins first).
"""

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engine.dsl import Condition
from app.engine.evaluator import evaluate_condition
from app.engine.input_validation import iso_date
from app.shared.domain.enums import DecisionType


class HitPolicy(StrEnum):
    FIRST_MATCH = "FIRST_MATCH"
    PRIORITY = "PRIORITY"


class LimitFromField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    pct: float = Field(gt=0, le=1)


class TableOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    risk_grade: str | None = Field(default=None, min_length=1, max_length=5)
    reason_code: str | None = None
    approved_limit: float | None = None
    approved_limit_pct_of: LimitFromField | None = None
    approved_tenor_months: int | None = None
    pricing_rate: float | None = None


class TableRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int = 0
    conditions: list[Condition]
    output: TableOutput


class DecisionTableConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hit_policy: HitPolicy = HitPolicy.FIRST_MATCH
    rows: list[TableRow] = Field(min_length=1)
    no_match_decision: DecisionType = DecisionType.MANUAL_REVIEW
    no_match_reason_code: str | None = None
    # When the matched output approves with a limit below the requested amount,
    # escalate to APPROVE_WITH_CONDITION and add this reason code (configurable
    # policy mechanics, not hardcoded policy).
    above_limit_reason_code: str | None = None


class TableEvaluation(BaseModel):
    matched: bool
    row_index: int | None = None
    output: TableOutput
    row_details: list[dict[str, Any]]


def parse_decision_table_config(config_json: dict[str, Any]) -> DecisionTableConfig:
    return DecisionTableConfig.model_validate(config_json)


def evaluate_decision_table(
    config: DecisionTableConfig, features: dict[str, Any]
) -> TableEvaluation:
    ordered = list(enumerate(config.rows))
    if config.hit_policy is HitPolicy.PRIORITY:
        ordered.sort(key=lambda pair: pair[1].priority)

    row_details: list[dict[str, Any]] = []
    for index, row in ordered:
        condition_details = []
        matched = True
        for condition in row.conditions:
            result, detail = evaluate_condition(condition, features)
            condition_details.append(detail)
            matched = matched and result
        row_details.append(
            {
                "row_index": index,
                "priority": row.priority,
                "matched": matched,
                "conditions": condition_details,
            }
        )
        if matched:
            return TableEvaluation(
                matched=True, row_index=index, output=row.output, row_details=row_details
            )

    fallback = TableOutput(
        decision=config.no_match_decision, reason_code=config.no_match_reason_code
    )
    return TableEvaluation(matched=False, row_index=None, output=fallback, row_details=row_details)


def find_overlapping_rows(config: DecisionTableConfig) -> list[tuple[int, int]]:
    """Flag row pairs that can match the same input (docs/02 §6.4).

    Conservative satisfiability check per shared field: numeric ranges are
    intersected; equality/membership sets are intersected. Rows that do not
    share any field trivially overlap and are flagged.
    """
    overlaps: list[tuple[int, int]] = []
    for i in range(len(config.rows)):
        for j in range(i + 1, len(config.rows)):
            if _rows_may_overlap(config.rows[i], config.rows[j]):
                overlaps.append((i, j))
    return overlaps


def _rows_may_overlap(row_a: TableRow, row_b: TableRow) -> bool:
    fields_a = {c.field for c in row_a.conditions}
    fields_b = {c.field for c in row_b.conditions}
    for field in fields_a & fields_b:
        conds = [c for c in row_a.conditions + row_b.conditions if c.field == field]
        if not _conditions_satisfiable_together(conds):
            return False
    return True


def _conditions_satisfiable_together(conditions: list[Condition]) -> bool:
    allowed: list[Any] | None = None
    for condition in conditions:
        if condition.operator.value == "=":
            allowed = [condition.value]
            break
        if condition.operator.value == "in":
            allowed = condition.value
            break
    if allowed is not None:
        return any(
            all(evaluate_condition(c, {c.field: value})[0] for c in conditions) for value in allowed
        )

    lower: int | float = float("-inf")
    upper: int | float = float("inf")
    lower_inclusive = upper_inclusive = True
    domain: str | None = None
    for condition in conditions:
        op, value = condition.operator.value, condition.value
        if op not in {">", ">=", "<", "<="}:
            continue
        current_domain = "date" if iso_date(value) else "number"
        if domain is not None and domain != current_domain:
            return False
        domain = current_domain
        boundary = date.fromisoformat(value).toordinal() if domain == "date" else value
        if op in {">", ">="}:
            inclusive = op == ">="
            if boundary > lower:
                lower, lower_inclusive = boundary, inclusive
            elif boundary == lower:
                lower_inclusive = lower_inclusive and inclusive
        else:
            inclusive = op == "<="
            if boundary < upper:
                upper, upper_inclusive = boundary, inclusive
            elif boundary == upper:
                upper_inclusive = upper_inclusive and inclusive
    if lower > upper:
        return False
    if lower == upper:
        if not (lower_inclusive and upper_inclusive):
            return False
        candidate = date.fromordinal(int(lower)).isoformat() if domain == "date" else lower
        return all(evaluate_condition(c, {c.field: candidate})[0] for c in conditions)
    # Remaining unconstrained/excluded regions are conservatively flagged, never executed.
    return True
