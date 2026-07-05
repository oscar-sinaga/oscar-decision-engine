"""Feature catalog helpers shared by rule/strategy validation and metadata."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.features import (
    DERIVED_FEATURES,
    PAYLOAD_FEATURES,
    SCORE_FEATURES,
)
from app.modules.features.models import Feature
from app.shared.domain.enums import FeatureDataType, FeatureSource

# Feature paths whose values are booleans / known non-numeric, used to seed the
# catalog data types accurately. Everything else defaults to NUMBER unless the
# path implies a string.
_BOOLEAN_PATHS = {
    "fraud.identity_match",
    "fraud.document_match",
    "fraud.blacklist_hit",
}
_STRING_PATHS = {
    "application.product_type",
    "application.channel",
    "applicant.customer_id",
    "applicant.employment_type",
    "vehicle.type",
    "vehicle.brand",
    "vehicle.model",
    "vehicle.ownership_status",
    "bureau.collectability",
    "model_outputs.model_version",
    "score.risk_grade",
}


def _category_for(path: str) -> str:
    return path.split(".", 1)[0].upper()


def _data_type_for(path: str) -> FeatureDataType:
    if path in _BOOLEAN_PATHS:
        return FeatureDataType.BOOLEAN
    if path in _STRING_PATHS:
        return FeatureDataType.STRING
    return FeatureDataType.NUMBER


def catalog_seed_rows() -> list[dict[str, object]]:
    """Catalog rows mirroring the engine's known features (idempotent seed)."""
    rows: list[dict[str, object]] = []
    for path, description in PAYLOAD_FEATURES.items():
        rows.append(_row(path, description, FeatureSource.PAYLOAD))
    for path, description in DERIVED_FEATURES.items():
        rows.append(_row(path, description, FeatureSource.DERIVED))
    for path, description in SCORE_FEATURES.items():
        rows.append(_row(path, description, FeatureSource.SCORE))
    return rows


def _row(path: str, description: str, source: FeatureSource) -> dict[str, object]:
    return {
        "path": path,
        "label": path.split(".")[-1].replace("_", " ").title(),
        "description": description,
        "data_type": _data_type_for(path),
        "source": source,
        "category": _category_for(path),
    }


async def active_feature_paths(session: AsyncSession) -> set[str]:
    """Set of feature paths a rule/strategy may reference (governed vocabulary)."""
    rows = await session.scalars(select(Feature.path).where(Feature.active.is_(True)))
    return set(rows.all())
