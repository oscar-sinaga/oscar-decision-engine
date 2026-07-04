"""Canonical permission codes and default role→permission mapping (docs/14 §7).

The mapping is seed data, not enforcement logic: authorization always checks
the permission codes attached to the authenticated principal in the database.
"""


class Permissions:
    DECISION_EXECUTE = "decision.execute"
    DECISION_VIEW = "decision.view"
    DECISION_TRACE_VIEW = "decision.trace.view"
    RULE_VIEW = "rule.view"
    RULE_CREATE = "rule.create"
    RULE_APPROVE = "rule.approve"
    STRATEGY_VIEW = "strategy.view"
    STRATEGY_CREATE = "strategy.create"
    STRATEGY_ACTIVATE = "strategy.activate"
    REASON_CODE_VIEW = "reason_code.view"
    REASON_CODE_MANAGE = "reason_code.manage"
    SIMULATION_RUN = "simulation.run"
    SIMULATION_VIEW = "simulation.view"
    MANUAL_REVIEW_VIEW = "manual_review.view"
    MANUAL_REVIEW_DECIDE = "manual_review.decide"
    MANUAL_REVIEW_OVERRIDE = "manual_review.override"
    AUDIT_VIEW = "audit.view"
    MONITORING_VIEW = "monitoring.view"
    ADMIN_MANAGE = "admin.manage"
    PII_VIEW = "pii.view"
    DATA_EXPORT = "data.export"


ALL_PERMISSIONS: dict[str, str] = {
    Permissions.DECISION_EXECUTE: "Submit applications for decisioning",
    Permissions.DECISION_VIEW: "View decisions and decision history",
    Permissions.DECISION_TRACE_VIEW: "View decision traces",
    Permissions.RULE_VIEW: "View rules, decision tables, and scorecards",
    Permissions.RULE_CREATE: "Create and edit draft rules/decision tables/scorecards",
    Permissions.RULE_APPROVE: "Approve and activate rule versions",
    Permissions.STRATEGY_VIEW: "View strategies",
    Permissions.STRATEGY_CREATE: "Create and edit draft strategy versions",
    Permissions.STRATEGY_ACTIVATE: "Activate or roll back strategy versions",
    Permissions.REASON_CODE_VIEW: "View reason codes",
    Permissions.REASON_CODE_MANAGE: "Manage reason codes",
    Permissions.SIMULATION_RUN: "Run simulations",
    Permissions.SIMULATION_VIEW: "View simulation results",
    Permissions.MANUAL_REVIEW_VIEW: "View manual review queue and cases",
    Permissions.MANUAL_REVIEW_DECIDE: "Decide manual review cases",
    Permissions.MANUAL_REVIEW_OVERRIDE: "Override definitive system decisions",
    Permissions.AUDIT_VIEW: "View business audit events",
    Permissions.MONITORING_VIEW: "View monitoring metrics",
    Permissions.ADMIN_MANAGE: "Manage users, roles, and permissions",
    Permissions.PII_VIEW: "View unmasked PII where available",
    Permissions.DATA_EXPORT: "Export data",
}

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": list(ALL_PERMISSIONS),
    "RISK_ANALYST": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.RULE_VIEW,
        Permissions.RULE_CREATE,
        Permissions.STRATEGY_VIEW,
        Permissions.STRATEGY_CREATE,
        Permissions.REASON_CODE_VIEW,
        Permissions.REASON_CODE_MANAGE,
        Permissions.SIMULATION_RUN,
        Permissions.SIMULATION_VIEW,
        Permissions.MONITORING_VIEW,
    ],
    "RISK_MANAGER": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.RULE_VIEW,
        Permissions.RULE_CREATE,
        Permissions.RULE_APPROVE,
        Permissions.STRATEGY_VIEW,
        Permissions.STRATEGY_CREATE,
        Permissions.STRATEGY_ACTIVATE,
        Permissions.REASON_CODE_VIEW,
        Permissions.REASON_CODE_MANAGE,
        Permissions.SIMULATION_RUN,
        Permissions.SIMULATION_VIEW,
        Permissions.MANUAL_REVIEW_VIEW,
        Permissions.MANUAL_REVIEW_DECIDE,
        Permissions.MANUAL_REVIEW_OVERRIDE,
        Permissions.AUDIT_VIEW,
        Permissions.MONITORING_VIEW,
    ],
    "UNDERWRITER": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.REASON_CODE_VIEW,
        Permissions.MANUAL_REVIEW_VIEW,
        Permissions.MANUAL_REVIEW_DECIDE,
    ],
    "COMPLIANCE": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.REASON_CODE_VIEW,
        Permissions.AUDIT_VIEW,
        Permissions.PII_VIEW,
        Permissions.DATA_EXPORT,
    ],
    "DATA_SCIENTIST": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.SIMULATION_RUN,
        Permissions.SIMULATION_VIEW,
        Permissions.MONITORING_VIEW,
    ],
    "ENGINEER": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.MONITORING_VIEW,
    ],
    "AUDITOR": [
        Permissions.DECISION_VIEW,
        Permissions.DECISION_TRACE_VIEW,
        Permissions.RULE_VIEW,
        Permissions.STRATEGY_VIEW,
        Permissions.REASON_CODE_VIEW,
        Permissions.MANUAL_REVIEW_VIEW,
        Permissions.AUDIT_VIEW,
        Permissions.MONITORING_VIEW,
    ],
    "API_CLIENT": [
        Permissions.DECISION_EXECUTE,
        Permissions.DECISION_VIEW,
    ],
}
