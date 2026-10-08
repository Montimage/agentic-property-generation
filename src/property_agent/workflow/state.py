import operator

from typing import Annotated

from typing_extensions import TypedDict

from property_agent.models import (
    CompilationResult,
    FinalPropertyAssessment,
    GeneratedProperty,
    MonitoringTask,
    PropertyGenerationResult,
    RepairDiagnosis,
    RepairResult,
    RetrievalResult,
    SemanticReport,
    ValidationResult,
)


class PropertyWorkflowState(
    TypedDict,
    total=False,
):
    """
    Shared LangGraph state for one monitoring task.

    Most fields use normal overwrite semantics.

    property_history and repair_history use reducers so
    individual graph nodes can append entries.
    """

    task: MonitoringTask

    retrieval_result: RetrievalResult | None

    current_property: GeneratedProperty | None

    property_history: Annotated[
        list[GeneratedProperty],
        operator.add,
    ]

    xml_validation: ValidationResult | None

    syntax_validation: ValidationResult | None

    static_validation: ValidationResult | None

    semantic_report: SemanticReport | None

    repair_diagnosis: RepairDiagnosis | None

    repair_result: RepairResult | None

    repair_history: Annotated[
        list[RepairResult],
        operator.add,
    ]

    compilation_result: CompilationResult | None

    final_assessment: (
        FinalPropertyAssessment | None
    )

    result: PropertyGenerationResult | None

    repair_count: int

    max_repair_attempts: int

    terminal_reason: str | None

    workflow_error: str | None