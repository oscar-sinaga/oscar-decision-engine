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


def test_sensitive_key_matching() -> None:
    assert is_sensitive_key("X-Api-Key")
    assert is_sensitive_key("customer_phone_number")
    assert not is_sensitive_key("requested_amount")
    assert not is_sensitive_key("risk_grade")
