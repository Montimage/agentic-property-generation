from typing import Any
from pydantic import BaseModel, Field

class MonitoringTask(BaseModel):
    """Natural-language monitoring requirement to be implemented as a property."""

    id: str = Field(
        ...,
        description="Unique identifier of the monitoring task.",
    )

    property_id: str

    description: str = Field(
        ...,
        description="Natural-language description of the behavior to monitor.",
    )

    protocols: list[str] = Field(
        ...,
        min_length=1,
        description="Protocols involved in the monitoring task.",
    )

    monitoring_point: str | None = Field(
        default=None,
        description="Network or system point where the property will be evaluated.",
    )

    requirements: list[str] = Field(
        default_factory=list,
        description="Explicit functional requirements that the property must satisfy.",
    )

    restrictions: list[str] = Field(
        default_factory=list,
        description="Restrictions that constrain property generation.",
    )

    expected_behavior: str | None = Field(
        default=None,
        description="Human-readable description of the expected monitoring behavior.",
    )

    ambiguities: list[str] = Field(
        default_factory=list
    )

    assumptions: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata associated with the task.",
    )