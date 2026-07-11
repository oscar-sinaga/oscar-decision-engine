"""Aggregated model imports for Alembic autogenerate.

Every module that defines ORM models must be imported here so
``Base.metadata`` is complete when migrations are generated.
"""

from app.modules.audit.models import AuditLog
from app.modules.auth.models import Permission, Role, User
from app.modules.decisions.models import Application, Decision, DecisionTrace
from app.modules.features.models import Feature
from app.modules.governance.models import ApprovalRequest
from app.modules.manual_review.models import (
    ManualReviewCase,
    ManualReviewComment,
    ManualReviewDocument,
)
from app.modules.model_registry.models import RegisteredModel
from app.modules.reason_codes.models import ReasonCode
from app.modules.rules.models import Rule, RuleCategory, RuleSet, RuleSetMember, RuleVersion
from app.modules.scorecards.models import (
    DecisionTable,
    DecisionTableVersion,
    Scorecard,
    ScorecardVersion,
)
from app.modules.simulations.models import Simulation, SimulationResult
from app.modules.strategies.models import Strategy, StrategyStep, StrategyVersion

__all__ = [
    "Application",
    "ApprovalRequest",
    "AuditLog",
    "Decision",
    "DecisionTable",
    "DecisionTableVersion",
    "DecisionTrace",
    "Feature",
    "ManualReviewCase",
    "ManualReviewComment",
    "ManualReviewDocument",
    "Permission",
    "ReasonCode",
    "RegisteredModel",
    "Role",
    "Rule",
    "RuleCategory",
    "RuleSet",
    "RuleSetMember",
    "RuleVersion",
    "Scorecard",
    "ScorecardVersion",
    "Simulation",
    "SimulationResult",
    "Strategy",
    "StrategyStep",
    "StrategyVersion",
    "User",
]
