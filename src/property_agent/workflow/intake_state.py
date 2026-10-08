from typing import TypedDict

from property_agent.models import (
    MonitoringTask,
    NaturalLanguageScenario,
    TaskInterpretationResult,
    TaskClarificationResponse,
)


class TaskIntakeState(
    TypedDict,
    total=False,
):
    """
    State used by the natural-language task intake and
    clarification workflow.
    """

    scenario: NaturalLanguageScenario

    interpretation_result: (
        TaskInterpretationResult
    )

    task: MonitoringTask

    clarification_response: (
        TaskClarificationResponse | None
    )

    assume_remaining: bool

    cancelled: bool

    clarification_round: int

    max_clarification_rounds: int

    complete: bool

    terminal_reason: str | None