from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


SemanticScore = Literal[0.0, 0.5, 1.0]


class SemanticIssueType(str, Enum):
    """
    Origin or nature of a semantic-validation issue.
    """

    PROPERTY_LOGIC_ERROR = "property_logic_error"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    TEMPORAL_MISMATCH = "temporal_mismatch"
    ATTRIBUTE_IRRELEVANT = "attribute_irrelevant"
    KNOWLEDGE_MISSING = "knowledge_missing"
    TASK_UNDERSPECIFIED = "task_underspecified"


class SemanticIssue(BaseModel):
    """
    Structured issue identified during semantic validation.
    """

    type: SemanticIssueType

    message: str = Field(
        ...,
        description=(
            "Concise description of the semantic problem "
            "or uncertainty."
        ),
    )

    evidence: str | None = Field(
        default=None,
        description=(
            "Relevant property fragment, task requirement, "
            "or knowledge limitation supporting the issue."
        ),
    )


class SemanticDimensionResult(BaseModel):
    """
    Assessment of one semantic dimension.
    """

    score: SemanticScore = Field(
        ...,
        description=(
            "Semantic score: 1.0 aligned, "
            "0.5 partially aligned or uncertain, "
            "0.0 not aligned."
        ),
    )

    justification: str = Field(
        ...,
        description=(
            "Concise explanation supporting the assigned score."
        ),
    )

    issues: list[SemanticIssue] = Field(
        default_factory=list,
        description=(
            "Structured semantic issues identified "
            "for this dimension."
        ),
    )


class SemanticAssessment(BaseModel):
    """
    Semantic assessment returned by the LLM reviewer.

    The reviewer evaluates the four semantic dimensions,
    but does not determine the final acceptance policy.
    """

    message_exchange_semantics: SemanticDimensionResult

    temporal_ordering_semantics: SemanticDimensionResult

    detection_semantics: SemanticDimensionResult

    attribute_relevance: SemanticDimensionResult

    summary: str

    recommendations: list[str] = Field(
        default_factory=list,
    )


class SemanticReport(BaseModel):
    """
    Final semantic-validation report.

    overall_score and valid are calculated deterministically
    by the semantic-validation workflow rather than trusted
    directly from the LLM.
    """

    message_exchange_semantics: SemanticDimensionResult

    temporal_ordering_semantics: SemanticDimensionResult

    detection_semantics: SemanticDimensionResult

    attribute_relevance: SemanticDimensionResult

    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    valid: bool

    summary: str

    recommendations: list[str] = Field(
        default_factory=list,
    )