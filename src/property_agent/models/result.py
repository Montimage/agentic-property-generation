from typing import Any

from pydantic import BaseModel, Field

from .assessment import FinalPropertyAssessment
from .compilation import CompilationResult
from .property import GeneratedProperty
from .repair import RepairResult
from .semantic import SemanticReport
from .validation import ValidationResult


class PropertyGenerationResult(BaseModel):
    """
    Complete result associated with the generation and
    validation of one MMT monitoring property.

    This model collects the outputs produced by the
    different stages of the property-generation pipeline.

    Workflow orchestration is responsible for populating
    these fields.
    """

    task_id: str

    success: bool

    property: GeneratedProperty | None = None

    xml_validation: ValidationResult | None = None

    syntax_validation: ValidationResult | None = None

    static_validation: ValidationResult | None = None

    semantic_validation: SemanticReport | None = None

    repair_result: RepairResult | None = None

    compilation_validation: CompilationResult | None = None

    final_assessment: FinalPropertyAssessment | None = None

    attempts: int = Field(
        default=0,
        ge=0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )