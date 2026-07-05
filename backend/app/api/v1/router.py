"""Aggregated ``/v1`` API router."""

from fastapi import APIRouter

from app.api.v1.meta import router as meta_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.decisions.router import router as decisions_router
from app.modules.features.router import router as features_router
from app.modules.governance.router import admin_router
from app.modules.governance.router import router as governance_router
from app.modules.manual_review.router import router as manual_review_router
from app.modules.model_registry.router import router as model_registry_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.reason_codes.router import router as reason_codes_router
from app.modules.rules.router import router as rules_router
from app.modules.rules.rule_sets_router import router as rule_sets_router
from app.modules.scorecards.router import decision_tables_router, scorecards_router
from app.modules.simulations.router import router as simulations_router
from app.modules.strategies.router import router as strategies_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(decisions_router)
api_router.include_router(rules_router)
api_router.include_router(rule_sets_router)
api_router.include_router(features_router)
api_router.include_router(decision_tables_router)
api_router.include_router(scorecards_router)
api_router.include_router(manual_review_router)
api_router.include_router(monitoring_router)
api_router.include_router(model_registry_router)
api_router.include_router(reason_codes_router)
api_router.include_router(simulations_router)
api_router.include_router(strategies_router)
api_router.include_router(audit_router)
api_router.include_router(governance_router)
api_router.include_router(admin_router)
api_router.include_router(meta_router)
