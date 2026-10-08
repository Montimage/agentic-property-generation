from enum import Enum

from pydantic import BaseModel, Field

from .compilation import CompilationResult


class FinalAssessmentStatus(str, Enum):
    """
    Final disposition of a generated property.
    """

    ACCEPTED = "accepted"

    REJECTED_VALIDATION = "rejected_validation"

    REJECTED_SEMANTIC = "rejected_semantic"

    REJECTED_COMPILATION = "rejected_compilation"

    BLOCKED = "blocked"

    INCONCLUSIVE = "inconclusive"


class AssessmentStatistics(BaseModel):
    """
    Statistics retained for experimental evaluation.
    """

    final_attempt: int

    deterministic_error_count: int = 0

    deterministic_warning_count: int = 0

    semantic_issue_count: int = 0

    semantic_overall_score: float | None = None

    compilation_duration_ms: int | None = None

    compilation_returncode: int | None = None

    local_compiler_agreement: bool | None = None

    repair_performed: bool = False


class FinalPropertyAssessment(BaseModel):
    """
    Deterministic final assessment of one generated
    monitoring property.
    """

    task_id: str

    property_id: str

    status: FinalAssessmentStatus

    xml_valid: bool | None = None

    syntax_valid: bool | None = None

    static_valid: bool | None = None

    semantic_valid: bool | None = None

    semantic_score: float | None = None

    compilation: CompilationResult | None = None

    statistics: AssessmentStatistics

    reasons: list[str] = Field(
        default_factory=list
    )