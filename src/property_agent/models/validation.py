from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """Individual problem reported by a validator."""

    code: str = Field(
        ...,
        description="Machine-readable error or warning identifier.",
    )

    message: str = Field(
        ...,
        description="Human-readable description of the issue.",
    )

    severity: ValidationSeverity = ValidationSeverity.ERROR

    line: int | None = Field(
        default=None,
        ge=1,
        description="XML line associated with the issue when available.",
    )

    column: int | None = Field(
        default=None,
        ge=1,
        description="XML column associated with the issue when available.",
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional validator-specific information.",
    )


class ValidationResult(BaseModel):
    """Standard result returned by deterministic validation tools."""

    validator: str = Field(
        ...,
        description="Name of the validator that produced the result.",
    )

    valid: bool

    issues: list[ValidationIssue] = Field(
        default_factory=list,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )