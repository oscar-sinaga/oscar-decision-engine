"""Feature registry and derived-feature calculations.

The registry is the controlled vocabulary for rule conditions (docs/10 §2):
rules may only reference fields listed here, which keeps the condition
builder safe and validation deterministic.

Derived calculations are *engine mechanics* — deterministic arithmetic over
payload values. Credit-policy thresholds never live here; they belong to
configurable rules and decision tables.
"""

from collections.abc import Collection
from datetime import UTC, datetime
from typing import Any

from app.engine.input_validation import finite_number

FeatureMap = dict[str, Any]

# Payload fields exposed to rules (path -> human description).
PAYLOAD_FEATURES: dict[str, str] = {
    "application.product_type": "Product type of the application",
    "application.channel": "Submission channel",
    "applicant.customer_id": "Internal customer reference",
    "applicant.age": "Applicant age in years",
    "applicant.employment_type": "Employment type",
    "applicant.monthly_income": "Declared monthly income",
    "applicant.existing_monthly_obligation": "Existing monthly obligations",
    "applicant.internal_max_dpd_12m": "Internal max days-past-due last 12 months",
    "loan.requested_amount": "Requested financing amount",
    "loan.requested_tenor_months": "Requested tenor in months",
    "vehicle.type": "Collateral vehicle type",
    "vehicle.brand": "Vehicle brand",
    "vehicle.model": "Vehicle model",
    "vehicle.year": "Vehicle production year",
    "vehicle.appraisal_value": "Appraised collateral value",
    "vehicle.ownership_status": "Vehicle ownership status",
    "bureau.collectability": "Bureau collectability status",
    "bureau.max_dpd_12m": "Bureau max days-past-due last 12 months",
    "bureau.active_loan_count": "Number of active loans",
    "fraud.identity_match": "eKYC identity match flag",
    "fraud.document_match": "Document verification match flag",
    "fraud.blacklist_hit": "Internal/external blacklist hit flag",
    "fraud.device_risk_score": "Device risk score 0..1",
    "model_outputs.credit_score": "External model credit score",
    "model_outputs.model_version": "External model version identifier",
}

# Derived features computed by CALCULATION steps (code -> description).
DERIVED_FEATURES: dict[str, str] = {
    "loan.ltv": "requested_amount / appraisal_value",
    "vehicle.age_years": "current year - vehicle.year (at execution time)",
    "affordability.estimated_installment": "requested_amount / requested_tenor_months",
    "affordability.dti": "(existing_obligation + estimated_installment) / monthly_income",
}

# Features produced by scorecard steps.
SCORE_FEATURES: dict[str, str] = {
    "score.value": "Resolved credit score",
    "score.risk_grade": "Risk grade mapped from score bands",
}

KNOWN_FEATURES: dict[str, str] = {**PAYLOAD_FEATURES, **DERIVED_FEATURES, **SCORE_FEATURES}


def flatten_payload(payload: dict[str, Any], prefix: str = "") -> FeatureMap:
    """Flatten a nested payload into dotted paths: {"loan": {"ltv": 1}} -> {"loan.ltv": 1}."""
    flat: FeatureMap = {}
    for key, value in payload.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten_payload(value, prefix=f"{path}."))
        else:
            flat[path] = value
    return flat


def build_base_features(
    payload: dict[str, Any], *, payload_paths: Collection[str] | None = None
) -> FeatureMap:
    """Feature map from the raw application payload (before calculations)."""
    flat = flatten_payload(payload)
    paths = PAYLOAD_FEATURES if payload_paths is None else payload_paths
    features = {path: flat[path] for path in paths if path in flat}
    # application.* metadata is provided at the top level of the payload.
    if "product_type" in payload:
        features["application.product_type"] = payload["product_type"]
    if "channel" in payload:
        features["application.channel"] = payload["channel"]
    return features


def _as_number(value: Any) -> float | None:
    return float(value) if finite_number(value) else None


def compute_derived_feature(code: str, features: FeatureMap, *, now: datetime | None = None) -> Any:
    """Compute one derived feature; returns ``None`` when inputs are missing/invalid."""
    if code == "loan.ltv":
        amount = _as_number(features.get("loan.requested_amount"))
        appraisal = _as_number(features.get("vehicle.appraisal_value"))
        if amount is None or appraisal is None or appraisal <= 0:
            return None
        return round(amount / appraisal, 6)
    if code == "vehicle.age_years":
        year = _as_number(features.get("vehicle.year"))
        if year is None:
            return None
        current_year = (now or datetime.now(UTC)).year
        return int(current_year - int(year))
    if code == "affordability.estimated_installment":
        amount = _as_number(features.get("loan.requested_amount"))
        tenor = _as_number(features.get("loan.requested_tenor_months"))
        if amount is None or tenor is None or tenor <= 0:
            return None
        return round(amount / tenor, 2)
    if code == "affordability.dti":
        income = _as_number(features.get("applicant.monthly_income"))
        obligation = _as_number(features.get("applicant.existing_monthly_obligation")) or 0.0
        installment = _as_number(features.get("affordability.estimated_installment"))
        if installment is None:
            installment = compute_derived_feature("affordability.estimated_installment", features)
        if income is None or income <= 0 or installment is None:
            return None
        return round((obligation + float(installment)) / income, 6)
    raise KeyError(f"Unknown derived feature: {code}")
