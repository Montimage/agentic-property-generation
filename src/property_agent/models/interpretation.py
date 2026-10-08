from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from .task import MonitoringTask


class ClarificationAction(
    str,
    Enum,
):
    CLARIFY = "clarify"
    ASSUME_REMAINING = "assume_remaining"
    CANCEL = "cancel"


class TaskClarificationResponse(
    BaseModel
):
    """
    Decision supplied by the user when the intake
    workflow identifies unresolved task ambiguities.
    """

    action: ClarificationAction

    text: str | None = None

    @model_validator(
        mode="after"
    )
    def validate_response(
        self,
    ):
        if (
            self.action
            == ClarificationAction.CLARIFY
        ):
            if (
                self.text is None
                or not self.text.strip()
            ):
                raise ValueError(
                    "A clarification response "
                    "requires non-empty text."
                )

        if self.text is not None:
            self.text = self.text.strip()

        return self

class TaskTextUpdate(
    BaseModel
):
    """
    One deterministic textual update to a canonical
    task field.

    When `previous` is None, `value` is a new item.

    When `previous` is supplied, it must exactly match
    an existing item and `value` replaces it.
    """

    previous: str | None = None

    value: str

    @model_validator(
        mode="after"
    )
    def normalize_update(
        self,
    ):
        if self.previous is not None:
            self.previous = (
                self.previous.strip()
            )

            if not self.previous:
                self.previous = None

        self.value = self.value.strip()

        if not self.value:
            raise ValueError(
                "Task update value cannot be empty."
            )

        return self

class TaskAssumptionResolution(
    BaseModel
):
    """
    Structured result produced after the user explicitly
    authorizes resolution of remaining task-level
    ambiguities.

    Assumptions may refine only requirements associated
    with authorized ambiguities.
    """

    requirement_updates: list[
        TaskTextUpdate
    ] = Field(
        default_factory=list
    )

    assumptions: list[str] = Field(
        default_factory=list
    )

    resolved_ambiguities: list[str] = Field(
        default_factory=list
    )

class NaturalLanguageScenario(
    BaseModel
):
    """
    External natural-language description of a
    monitoring objective.

    Identifiers are assigned externally.

    Clarifications contain additional information
    explicitly supplied by the user after the initial
    scenario was interpreted.
    """

    id: str

    property_id: str

    text: str

    clarifications: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class TaskInterpretation(
    BaseModel
):
    """
    Structured semantic extraction produced by the
    task-interpreter LLM.

    This model deliberately excludes id and property_id.
    Those values are controlled by the calling system.
    """

    description: str

    protocols: list[str] = Field(
        default_factory=list
    )

    monitoring_point: str | None = None

    requirements: list[str] = Field(
        default_factory=list
    )

    restrictions: list[str] = Field(
        default_factory=list
    )

    expected_behavior: str | None = None

    ambiguities: list[str] = Field(
        default_factory=list
    )


class TaskInterpretationResult(
    BaseModel
):
    """
    Complete result of natural-language task
    interpretation.

    The interpreted MonitoringTask becomes the
    canonical internal representation used by the
    remaining workflow.
    """

    scenario_id: str

    task: MonitoringTask

    model: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class TaskClarificationUpdate(
    BaseModel
):
    """
    Structured delta extracted from one explicit user
    clarification.

    Existing task information is changed only through
    explicit update operations.

    This prevents the clarification LLM from rebuilding
    or silently dropping unrelated task information.
    """

    requirement_updates: list[
        TaskTextUpdate
    ] = Field(
        default_factory=list
    )

    restriction_updates: list[
        TaskTextUpdate
    ] = Field(
        default_factory=list
    )

    protocols_to_add: list[str] = Field(
        default_factory=list
    )

    monitoring_point: str | None = None

    expected_behavior: str | None = None

    resolved_ambiguities: list[str] = Field(
        default_factory=list
    )

    new_ambiguities: list[str] = Field(
        default_factory=list
    )