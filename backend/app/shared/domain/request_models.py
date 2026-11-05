"""Storage-safe request models and explicit PATCH omission/null semantics."""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.engine.input_validation import validate_payload_json


class StorageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_storage_values(self) -> Self:
        # Catalog metadata may use dotted keys; runtime application paths may not.
        validate_payload_json(self.model_dump(), undotted_keys=False)
        return self


class PatchRequest(StorageRequest):
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def reject_null_for_required_columns(self) -> Self:
        for field in sorted(self.model_fields_set - self.nullable_fields):
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null; omit it to leave it unchanged")
        return self
