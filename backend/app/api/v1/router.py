"""Aggregated ``/v1`` API router."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.decisions.router import router as decisions_router
from app.modules.reason_codes.router import router as reason_codes_router
from app.modules.rules.router import router as rules_router
from app.modules.rules.rule_sets_router import router as rule_sets_router
from app.modules.scorecards.router import decision_tables_router, scorecards_router
from app.modules.strategies.router import router as strategies_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(decisions_router)
api_router.include_router(rules_router)
api_router.include_router(rule_sets_router)
api_router.include_router(decision_tables_router)
api_router.include_router(scorecards_router)
api_router.include_router(reason_codes_router)
api_router.include_router(strategies_router)
