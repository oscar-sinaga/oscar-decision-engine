"""Synthetic seed data for development, tests, and demos.

Idempotent: safe to run repeatedly. Contains **no real customer data** — all
users, credentials, and policy values are synthetic (docs/17 §6).

Run with: ``uv run python -m app.seed``
"""

import asyncio
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DecisionTable,
    DecisionTableVersion,
    Feature,
    Permission,
    ReasonCode,
    Role,
    Rule,
    RuleSet,
    RuleSetMember,
    RuleVersion,
    Scorecard,
    ScorecardVersion,
    Strategy,
    StrategyEdge,
    StrategyNode,
    StrategyVersion,
    User,
)
from app.modules.auth.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from app.modules.auth.security import hash_password
from app.modules.features.service import catalog_seed_rows
from app.modules.model_registry.models import RegisteredModel
from app.shared.config import get_settings
from app.shared.database.session import get_sessionmaker
from app.shared.domain.enums import (
    ActorType,
    ConfigStatus,
    NodeType,
    ProductType,
    ReasonCodeCategory,
    ReasonSeverity,
    RuleCategory,
    StepOnError,
    StepType,
)
from app.shared.logging import configure_logging, get_logger

logger = get_logger("oscar.seed")

# Synthetic demo credential shared by seeded users; override for demos via env.
SEED_PASSWORD = os.environ.get("OSCAR_SEED_PASSWORD", "OscarDemo123!")

SEED_USERS: list[dict[str, Any]] = [
    {"username": "admin", "full_name": "Ada Admin", "roles": ["ADMIN"]},
    {"username": "riskanalyst", "full_name": "Rani Risk Analyst", "roles": ["RISK_ANALYST"]},
    {"username": "riskmanager", "full_name": "Maya Risk Manager", "roles": ["RISK_MANAGER"]},
    {"username": "underwriter", "full_name": "Udin Underwriter", "roles": ["UNDERWRITER"]},
    {"username": "compliance", "full_name": "Cahya Compliance", "roles": ["COMPLIANCE"]},
    {"username": "datascientist", "full_name": "Dewi Data Scientist", "roles": ["DATA_SCIENTIST"]},
    {"username": "engineer", "full_name": "Eko Engineer", "roles": ["ENGINEER"]},
    {"username": "auditor", "full_name": "Anti Auditor", "roles": ["AUDITOR"]},
    {
        "username": "los-client",
        "full_name": "LOS API Client",
        "roles": ["API_CLIENT"],
        "actor_type": ActorType.API_CLIENT,
    },
]

SEED_REASON_CODES: list[dict[str, Any]] = [
    {
        "code": "APPLICANT_UNDER_MIN_AGE",
        "category": ReasonCodeCategory.ELIGIBILITY,
        "severity": ReasonSeverity.DECLINE,
        "internal_message": "Applicant age is below the minimum policy age",
        "customer_message": "The application does not meet our age requirement",
    },
    {
        "code": "VEHICLE_AGE_ABOVE_POLICY",
        "category": ReasonCodeCategory.COLLATERAL,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Vehicle age exceeds the policy maximum for this product",
        "customer_message": "The collateral vehicle requires additional review",
    },
    {
        "code": "LTV_ABOVE_THRESHOLD",
        "category": ReasonCodeCategory.COLLATERAL,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Loan-to-value ratio is above the configured threshold",
        "customer_message": "The requested amount requires additional review",
    },
    {
        "code": "HIGH_DTI",
        "category": ReasonCodeCategory.AFFORDABILITY,
        "severity": ReasonSeverity.DECLINE,
        "internal_message": "Debt-to-income ratio exceeds the maximum policy threshold",
        "customer_message": "The application does not meet our affordability criteria",
    },
    {
        "code": "DTI_NEAR_THRESHOLD",
        "category": ReasonCodeCategory.AFFORDABILITY,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Debt-to-income ratio is near the maximum policy threshold",
        "customer_message": "The application requires additional affordability review",
    },
    {
        "code": "BUREAU_BAD_HISTORY",
        "category": ReasonCodeCategory.BUREAU,
        "severity": ReasonSeverity.DECLINE,
        "internal_message": "Bureau data shows days-past-due beyond policy tolerance",
        "customer_message": "The application does not meet our credit history criteria",
    },
    {
        "code": "BLACKLIST_HIT",
        "category": ReasonCodeCategory.FRAUD,
        "severity": ReasonSeverity.DECLINE,
        "internal_message": "Applicant matched an internal/external blacklist entry",
        "customer_message": "The application cannot be processed",
    },
    {
        "code": "APPLICATION_DATA_MISMATCH",
        "category": ReasonCodeCategory.FRAUD,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Identity or document verification mismatch detected",
        "customer_message": "The application requires additional verification",
    },
    {
        "code": "SCORE_UNAVAILABLE",
        "category": ReasonCodeCategory.OPERATIONAL,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Credit score was unavailable at decision time",
        "customer_message": "The application requires additional review",
    },
    {
        "code": "RISK_GRADE_BORDERLINE",
        "category": ReasonCodeCategory.ELIGIBILITY,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Risk grade is borderline for automatic approval",
        "customer_message": "The application requires additional review",
    },
    {
        "code": "LOW_CREDIT_SCORE",
        "category": ReasonCodeCategory.ELIGIBILITY,
        "severity": ReasonSeverity.DECLINE,
        "internal_message": "Credit score below the approvable range",
        "customer_message": "The application does not meet our credit score criteria",
    },
    {
        "code": "REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT",
        "category": ReasonCodeCategory.LIMIT,
        "severity": ReasonSeverity.INFO,
        "internal_message": "Requested amount is above eligible limit",
        "customer_message": "We can offer a lower financing amount",
    },
    {
        "code": "NO_MATCHING_DECISION_ROW",
        "category": ReasonCodeCategory.OPERATIONAL,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "No decision-table row matched; conservative fallback applied",
        "customer_message": "The application requires additional review",
    },
    {
        "code": "NO_DECISION_PRODUCED",
        "category": ReasonCodeCategory.OPERATIONAL,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "Strategy produced no decision; conservative fallback applied",
        "customer_message": "The application requires additional review",
    },
    {
        "code": "STEP_EXECUTION_ERROR",
        "category": ReasonCodeCategory.OPERATIONAL,
        "severity": ReasonSeverity.REVIEW,
        "internal_message": "A strategy step failed; fallback path applied",
        "customer_message": "The application requires additional review",
    },
]

SEED_RULES: list[dict[str, Any]] = [
    {
        "rule_code": "MIN_AGE_STANDARD",
        "name": "Minimum Applicant Age",
        "category": RuleCategory.ELIGIBILITY,
        "condition": {"all": [{"field": "applicant.age", "operator": "<", "value": 21}]},
        "action": {"decision": "REJECT", "reason_code": "APPLICANT_UNDER_MIN_AGE"},
    },
    {
        "rule_code": "VEHICLE_AGE_MAX_MOTOR",
        "name": "Maximum Vehicle Age for Motor",
        "category": RuleCategory.COLLATERAL,
        "condition": {
            "all": [
                {"field": "vehicle.type", "operator": "=", "value": "MOTOR"},
                {"field": "vehicle.age_years", "operator": ">", "value": 8},
            ]
        },
        "action": {"decision": "MANUAL_REVIEW", "reason_code": "VEHICLE_AGE_ABOVE_POLICY"},
    },
    {
        "rule_code": "LTV_MAX_MOTOR",
        "name": "Maximum LTV for Motor Leaseback",
        "category": RuleCategory.COLLATERAL,
        "condition": {"all": [{"field": "loan.ltv", "operator": ">", "value": 0.85}]},
        "action": {"decision": "MANUAL_REVIEW", "reason_code": "LTV_ABOVE_THRESHOLD"},
    },
    {
        "rule_code": "DTI_MAX_STANDARD",
        "name": "Maximum DTI",
        "category": RuleCategory.AFFORDABILITY,
        "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.45}]},
        "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
    },
    {
        "rule_code": "DTI_NEAR_THRESHOLD",
        "name": "DTI Near Threshold",
        "category": RuleCategory.AFFORDABILITY,
        "condition": {
            "all": [
                {"field": "affordability.dti", "operator": ">", "value": 0.40},
                {"field": "affordability.dti", "operator": "<=", "value": 0.45},
            ]
        },
        "action": {"decision": "MANUAL_REVIEW", "reason_code": "DTI_NEAR_THRESHOLD"},
    },
    {
        "rule_code": "BUREAU_DPD_MAX",
        "name": "Bureau Max DPD 12M",
        "category": RuleCategory.BUREAU,
        "condition": {"all": [{"field": "bureau.max_dpd_12m", "operator": ">", "value": 30}]},
        "action": {"decision": "REJECT", "reason_code": "BUREAU_BAD_HISTORY"},
    },
    {
        "rule_code": "BLACKLIST_HIT",
        "name": "Blacklist Hit Hard Stop",
        "category": RuleCategory.FRAUD,
        "condition": {"all": [{"field": "fraud.blacklist_hit", "operator": "=", "value": True}]},
        "action": {
            "type": "STOP_EXECUTION",
            "decision": "REJECT",
            "reason_code": "BLACKLIST_HIT",
        },
    },
    {
        "rule_code": "DOCUMENT_IDENTITY_MISMATCH",
        "name": "Identity/Document Mismatch",
        "category": RuleCategory.FRAUD,
        "condition": {
            "any": [
                {"field": "fraud.identity_match", "operator": "=", "value": False},
                {"field": "fraud.document_match", "operator": "=", "value": False},
            ]
        },
        "action": {"decision": "FRAUD_INVESTIGATION", "reason_code": "APPLICATION_DATA_MISMATCH"},
    },
]

SEED_RULE_SETS: list[dict[str, Any]] = [
    {
        "code": "FRAUD_BASIC",
        "name": "Basic Fraud Screening",
        "rules": ["BLACKLIST_HIT", "DOCUMENT_IDENTITY_MISMATCH"],
    },
    {
        "code": "ELIGIBILITY_MOTOR",
        "name": "Motor Eligibility Rules",
        "rules": ["MIN_AGE_STANDARD", "VEHICLE_AGE_MAX_MOTOR", "LTV_MAX_MOTOR"],
    },
    {
        "code": "AFFORDABILITY_STANDARD",
        "name": "Standard Affordability Rules",
        "rules": ["DTI_MAX_STANDARD", "DTI_NEAR_THRESHOLD", "BUREAU_DPD_MAX"],
    },
]

MOTOR_SCORECARD_CONFIG: dict[str, Any] = {
    "score_field": "model_outputs.credit_score",
    "model_version_field": "model_outputs.model_version",
    "bands": [
        {"min_score": 750, "risk_grade": "A"},
        {"min_score": 650, "risk_grade": "B"},
        {"min_score": 550, "risk_grade": "C"},
        {"min_score": 450, "risk_grade": "D"},
    ],
    "below_bands_risk_grade": "E",
    "missing_score_decision": "MANUAL_REVIEW",
    "missing_score_reason_code": "SCORE_UNAVAILABLE",
}

FINAL_DECISION_MOTOR_CONFIG: dict[str, Any] = {
    "hit_policy": "FIRST_MATCH",
    "above_limit_reason_code": "REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT",
    "no_match_decision": "MANUAL_REVIEW",
    "no_match_reason_code": "NO_MATCHING_DECISION_ROW",
    "rows": [
        {
            "priority": 1,
            "conditions": [{"field": "score.risk_grade", "operator": "=", "value": "A"}],
            "output": {
                "decision": "APPROVE",
                "approved_limit_pct_of": {"field": "vehicle.appraisal_value", "pct": 0.9},
                "approved_tenor_months": 24,
                "pricing_rate": 0.019,
            },
        },
        {
            "priority": 2,
            "conditions": [{"field": "score.risk_grade", "operator": "=", "value": "B"}],
            "output": {
                "decision": "APPROVE",
                "approved_limit_pct_of": {"field": "vehicle.appraisal_value", "pct": 0.7},
                "approved_tenor_months": 18,
                "pricing_rate": 0.025,
            },
        },
        {
            "priority": 3,
            "conditions": [
                {"field": "score.risk_grade", "operator": "=", "value": "C"},
                {"field": "affordability.dti", "operator": "<=", "value": 0.35},
            ],
            "output": {
                "decision": "APPROVE",
                "approved_limit_pct_of": {"field": "vehicle.appraisal_value", "pct": 0.6},
                "approved_tenor_months": 12,
                "pricing_rate": 0.03,
            },
        },
        {
            "priority": 4,
            "conditions": [{"field": "score.risk_grade", "operator": "=", "value": "C"}],
            "output": {"decision": "MANUAL_REVIEW", "reason_code": "RISK_GRADE_BORDERLINE"},
        },
        {
            "priority": 5,
            "conditions": [{"field": "score.risk_grade", "operator": "in", "value": ["D", "E"]}],
            "output": {"decision": "REJECT", "reason_code": "LOW_CREDIT_SCORE"},
        },
    ],
}

LEASEBACK_MOTOR_STEPS: list[dict[str, Any]] = [
    {
        "order": 1,
        "type": StepType.VALIDATION,
        "name": "Required Fields",
        "reference_code": "REQUIRED_FIELDS",
        "config": {
            "required_fields": [
                "applicant.age",
                "applicant.monthly_income",
                "loan.requested_amount",
                "loan.requested_tenor_months",
                "vehicle.type",
                "vehicle.year",
                "vehicle.appraisal_value",
            ]
        },
    },
    {
        "order": 2,
        "type": StepType.CALCULATION,
        "name": "Derived Features",
        "reference_code": "AFFORDABILITY",
        "config": {
            "calculations": [
                "vehicle.age_years",
                "loan.ltv",
                "affordability.estimated_installment",
                "affordability.dti",
            ]
        },
    },
    {
        "order": 3,
        "type": StepType.RULE_SET,
        "name": "Fraud Screening",
        "reference_code": "FRAUD_BASIC",
    },
    {
        "order": 4,
        "type": StepType.RULE_SET,
        "name": "Eligibility Rules",
        "reference_code": "ELIGIBILITY_MOTOR",
    },
    {
        "order": 5,
        "type": StepType.RULE_SET,
        "name": "Affordability Rules",
        "reference_code": "AFFORDABILITY_STANDARD",
    },
    {
        "order": 6,
        "type": StepType.SCORECARD,
        "name": "Credit Score Banding",
        "reference_code": "MOTOR_SCORECARD",
        "on_error": StepOnError.MANUAL_REVIEW,
    },
    {
        "order": 7,
        "type": StepType.DECISION_TABLE,
        "name": "Final Decision Matrix",
        "reference_code": "FINAL_DECISION_MOTOR",
    },
]


async def seed_rbac(session: AsyncSession) -> None:
    existing_permissions = {p.code: p for p in (await session.scalars(select(Permission))).all()}
    for code, description in ALL_PERMISSIONS.items():
        if code not in existing_permissions:
            permission = Permission(code=code, description=description)
            session.add(permission)
            existing_permissions[code] = permission

    existing_roles = {r.code: r for r in (await session.scalars(select(Role))).all()}
    for role_code, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = existing_roles.get(role_code)
        if role is None:
            role = Role(code=role_code, name=role_code.replace("_", " ").title())
            session.add(role)
            existing_roles[role_code] = role
        role.permissions = [existing_permissions[code] for code in permission_codes]

    existing_users = {u.username: u for u in (await session.scalars(select(User))).all()}
    for spec in SEED_USERS:
        if spec["username"] in existing_users:
            continue
        user = User(
            username=spec["username"],
            full_name=spec["full_name"],
            hashed_password=hash_password(SEED_PASSWORD),
            actor_type=spec.get("actor_type", ActorType.USER),
        )
        user.roles = [existing_roles[code] for code in spec["roles"]]
        session.add(user)


async def seed_reason_codes(session: AsyncSession) -> None:
    existing = {rc.code for rc in (await session.scalars(select(ReasonCode))).all()}
    for spec in SEED_REASON_CODES:
        if spec["code"] in existing:
            continue
        session.add(ReasonCode(**spec))


async def seed_features(session: AsyncSession) -> None:
    existing = set((await session.scalars(select(Feature.path))).all())
    for row in catalog_seed_rows():
        if row["path"] in existing:
            continue
        session.add(Feature(**row))


async def seed_rules(session: AsyncSession) -> None:
    existing = {r.rule_code for r in (await session.scalars(select(Rule))).all()}
    for spec in SEED_RULES:
        if spec["rule_code"] in existing:
            continue
        rule = Rule(
            rule_code=spec["rule_code"],
            name=spec["name"],
            category=spec["category"],
            description=spec.get("description", ""),
        )
        session.add(rule)
        await session.flush()
        session.add(
            RuleVersion(
                rule_id=rule.id,
                version=1,
                status=ConfigStatus.ACTIVE,
                condition_json=spec["condition"],
                action_json=spec["action"],
                version_note="Initial synthetic policy",
            )
        )

    rule_by_code = {r.rule_code: r for r in (await session.scalars(select(Rule))).all()}
    existing_sets = {rs.code for rs in (await session.scalars(select(RuleSet))).all()}
    for set_spec in SEED_RULE_SETS:
        if set_spec["code"] in existing_sets:
            continue
        rule_set = RuleSet(code=set_spec["code"], name=set_spec["name"])
        session.add(rule_set)
        await session.flush()
        for order, rule_code in enumerate(set_spec["rules"], start=1):
            session.add(
                RuleSetMember(
                    rule_set_id=rule_set.id,
                    rule_id=rule_by_code[rule_code].id,
                    execution_order=order,
                )
            )


async def seed_scorecard_and_table(session: AsyncSession) -> None:
    scorecard = await session.scalar(select(Scorecard).where(Scorecard.code == "MOTOR_SCORECARD"))
    if scorecard is None:
        scorecard = Scorecard(code="MOTOR_SCORECARD", name="Motor Leaseback Scorecard")
        session.add(scorecard)
        await session.flush()
        session.add(
            ScorecardVersion(
                scorecard_id=scorecard.id,
                version=1,
                status=ConfigStatus.ACTIVE,
                config_json=MOTOR_SCORECARD_CONFIG,
                version_note="Initial synthetic bands",
            )
        )

    table = await session.scalar(
        select(DecisionTable).where(DecisionTable.code == "FINAL_DECISION_MOTOR")
    )
    if table is None:
        table = DecisionTable(code="FINAL_DECISION_MOTOR", name="Motor Final Decision Matrix")
        session.add(table)
        await session.flush()
        session.add(
            DecisionTableVersion(
                decision_table_id=table.id,
                version=1,
                status=ConfigStatus.ACTIVE,
                config_json=FINAL_DECISION_MOTOR_CONFIG,
                version_note="Initial synthetic matrix",
            )
        )


async def seed_strategy(session: AsyncSession) -> None:
    strategy = await session.scalar(
        select(Strategy).where(Strategy.strategy_code == "LEASEBACK_MOTOR")
    )
    if strategy is not None:
        return
    strategy = Strategy(
        strategy_code="LEASEBACK_MOTOR",
        name="Motor Leaseback Strategy",
        product_type=ProductType.MOTOR_LEASEBACK,
        segment="DEFAULT",
    )
    session.add(strategy)
    await session.flush()
    version = StrategyVersion(
        strategy_id=strategy.id,
        version=1,
        status=ConfigStatus.ACTIVE,
        version_note="Initial MVP strategy",
    )
    session.add(version)
    await session.flush()
    session.add(
        StrategyNode(
            strategy_version_id=version.id,
            node_key="start",
            node_type=NodeType.START,
            name="Start",
            position_x=0,
            position_y=0,
        )
    )
    previous = "start"
    for index, step in enumerate(LEASEBACK_MOTOR_STEPS, start=1):
        key = f"n{index}"
        step_type = StepType(step["type"])
        node_type = (
            NodeType.DECISION_TABLE if step_type is StepType.OUTPUT else NodeType(step_type.value)
        )
        session.add(
            StrategyNode(
                strategy_version_id=version.id,
                node_key=key,
                node_type=node_type,
                name=step["name"],
                reference_code=step.get("reference_code"),
                on_error=step.get("on_error", StepOnError.FAIL),
                config_json=step.get("config", {}),
                position_x=240 * index,
                position_y=0,
            )
        )
        session.add(
            StrategyEdge(
                strategy_version_id=version.id,
                from_node_key=previous,
                to_node_key=key,
            )
        )
        previous = key
    session.add(
        StrategyNode(
            strategy_version_id=version.id,
            node_key="end",
            node_type=NodeType.END,
            name="End",
            position_x=240 * (len(LEASEBACK_MOTOR_STEPS) + 1),
            position_y=0,
        )
    )
    session.add(
        StrategyEdge(
            strategy_version_id=version.id,
            from_node_key=previous,
            to_node_key="end",
        )
    )


async def seed_models(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(RegisteredModel).where(
            RegisteredModel.code == "MOTOR_SCORE", RegisteredModel.version_label == "V1"
        )
    )
    if existing is None:
        session.add(
            RegisteredModel(
                code="MOTOR_SCORE",
                version_label="V1",
                name="Motor Leaseback Credit Score",
                provider="INTERNAL",
                description="Synthetic scoring model referenced by MOTOR_SCORECARD.",
                metadata_json={
                    "payload_version_token": "MOTOR_SCORE_V1",
                    "score_range": [300, 850],
                },
            )
        )


async def seed_all(session: AsyncSession) -> None:
    await seed_rbac(session)
    await seed_features(session)
    await seed_reason_codes(session)
    await seed_rules(session)
    await seed_scorecard_and_table(session)
    await seed_strategy(session)
    await seed_models(session)
    await session.commit()
    logger.info("seed.completed")


async def main() -> None:
    # The synthetic accounts and policy values are development fixtures, never deployment data.
    if get_settings().environment.lower() not in {"development", "test", "testing", "compose", "local"}:
        raise RuntimeError("Synthetic demo seeding is disabled outside local development")
    configure_logging()
    async with get_sessionmaker()() as session:
        await seed_all(session)


if __name__ == "__main__":
    asyncio.run(main())
