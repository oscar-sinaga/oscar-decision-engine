"""Aggregated ``/v1`` API router."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.decisions.router import router as decisions_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(decisions_router)
