from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .result import (
    PropertyGenerationResult,
)

from .task import (
    MonitoringTask,
)


class NaturalLanguageWorkflowStatus(
    str,
    Enum,
):
    """
    High-level status exposed by the natural-language
    property-generation workflow.
    """

    CLARIFICATION_REQUIRED = (
        "clarification_required"
    )

    COMPLETED = "completed"

    BLOCKED = "blocked"

    CANCELLED = "cancelled"


class NaturalLanguageWorkflowResult(
    BaseModel
):
    """
    Public result of the natural-language workflow.

    Depending on the current state, the result either:

    - requests user clarification;
    - reports that intake was blocked;
    - reports user cancellation; or
    - contains the final property result.
    """

    status: NaturalLanguageWorkflowStatus

    thread_id: str

    task: MonitoringTask | None = None

    clarification_payload: (
        dict[str, Any] | None
    ) = None

    property_result: (
        PropertyGenerationResult | None
    ) = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )