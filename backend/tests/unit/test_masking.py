from app.shared.utils.masking import REDACTED, is_sensitive_key, redact, sanitize_snapshot


def test_redacts_sensitive_keys_recursively() -> None:
    payload = {
        "applicant": {
            "nik": "3174091202900001",
            "full_phone": "+628123456789",
            "home_address": "Jl. Sudirman 1",
            "monthly_income": 8_500_000,
        },
        "auth": {"access_token": "abc.def.ghi", "PASSWORD": "hunter2"},
        "documents": [{"document_url": "http://x/ktp.jpg"}],
    }
    result = redact(payload)
    assert result["applicant"]["nik"] == REDACTED
    assert result["applicant"]["full_phone"] == REDACTED
    assert result["applicant"]["home_address"] == REDACTED
    assert result["applicant"]["monthly_income"] == 8_500_000
    assert result["auth"]["access_token"] == REDACTED
    assert result["auth"]["PASSWORD"] == REDACTED
    # The key "documents" is itself sensitive, so the whole list is masked.
    assert result["documents"] == REDACTED


def test_snapshot_keeps_decision_relevant_fields() -> None:
    payload = {
        "application_id": "APP-1",
        "applicant": {"customer_id": "CUST-1", "age": 34, "nik": "317..."},
        "loan": {"requested_amount": 15_000_000},
    }
    snapshot = sanitize_snapshot(payload)
    assert snapshot["application_id"] == "APP-1"
    assert snapshot["applicant"]["age"] == 34
    assert snapshot["loan"]["requested_amount"] == 15_000_000
    assert snapshot["applicant"]["nik"] == REDACTED


def test_snapshot_masks_sensitive_dotted_output_keys() -> None:
    snapshot = sanitize_snapshot(
        {
            "outputs.synthetic_phone": "+620000000000",
            "outputs.eligible_limit": 12_500_000,
        }
    )
    assert snapshot["outputs.synthetic_phone"] == REDACTED
    assert snapshot["outputs.eligible_limit"] == 12_500_000


def test_sensitive_key_matching() -> None:
    assert is_sensitive_key("X-Api-Key")
    assert is_sensitive_key("customer_phone_number")
    assert not is_sensitive_key("requested_amount")
    assert not is_sensitive_key("risk_grade")


def test_trace_masks_sensitive_field_references_and_output_values() -> None:
    trace = {
        "field": "outputs.customer_phone",
        "actual": "+62812345678",
        "expected": "+62812345678",
        "operator": "EQ",
    }
    result = redact(trace)
    assert result["field"] == "outputs.customer_phone"
    assert result["actual"] == REDACTED
    assert result["expected"] == REDACTED
    assert result["operator"] == "EQ"
    assert redact({"outputs.synthetic_phone": "+62812345678"}) == {
        "outputs.synthetic_phone": REDACTED
    }
    assert redact({"applicant.customer_id": "PERSON-001"})["applicant.customer_id"] == REDACTED
