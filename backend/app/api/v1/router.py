"""Aggregated ``/v1`` API router."""

from fastapi import APIRouter

api_router = APIRouter(prefix="/v1")

# Feature routers are attached here as modules are implemented.
