from typing import Any

from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    """
    Configuration for verified-example retrieval.

    Retrieval is disabled by default so that the
    generation baseline remains unchanged.
    """

    enabled: bool = False

    k: int = Field(
        default=2,
        ge=1,
        le=10,
    )

    min_score: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
    )

    min_semantic_matches: int = Field(
        default=1,
        ge=0,
    )


class VerifiedExampleMetadata(BaseModel):
    """
    Metadata describing one curated property in the
    verified-example repository.
    """

    property_id: str

    file: str

    validated: bool

    property_type: str

    description: str

    protocols: list[str]

    tags: list[str] = Field(
        default_factory=list
    )

    constructs: list[str] = Field(
        default_factory=list
    )


class RetrievedExample(BaseModel):
    """
    One verified example selected for a monitoring task.
    """

    property_id: str

    file: str

    property_type: str

    description: str

    protocols: list[str]

    tags: list[str] = Field(
        default_factory=list
    )

    constructs: list[str] = Field(
        default_factory=list
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    matched_protocols: list[str] = Field(
        default_factory=list
    )

    matched_terms: list[str] = Field(
        default_factory=list
    )

    matched_tags: list[str] = Field(
        default_factory=list
    )

    xml: str


class RetrievalResult(BaseModel):
    """
    Complete retrieval result associated with one
    monitoring task.
    """

    task_id: str

    enabled: bool

    requested_k: int

    candidate_count: int = 0

    examples: list[RetrievedExample] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )