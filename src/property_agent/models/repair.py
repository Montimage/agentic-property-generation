from enum import Enum

from pydantic import BaseModel, Field

from .property import GeneratedProperty


class RepairIssueSource(str, Enum):
    """
    Source that identified a repair issue.
    """

    XML = "xml"
    MMT_SYNTAX = "mmt_syntax"
    MMT_STATIC = "mmt_static"
    SEMANTIC = "semantic"
    OTHER = "other"


class RepairDiagnosisStatus(str, Enum):
    """
    Result of deterministic repair diagnosis.
    """

    NO_REPAIR_NEEDED = "no_repair_needed"
    REPAIRABLE = "repairable"
    BLOCKED = "blocked"


class RepairOutcomeStatus(str, Enum):
    """
    Result of one repair invocation.
    """

    REPAIRED = "repaired"
    BLOCKED = "blocked"
    NOT_NEEDED = "not_needed"


class RepairIssue(BaseModel):
    """
    Normalized issue supplied to the repair agent.
    """

    source: RepairIssueSource

    code: str

    message: str

    evidence: str | None = None

    repairable: bool

    blocking: bool = False


class RepairDiagnosis(BaseModel):
    """
    Deterministic diagnosis of whether the current
    property can be safely repaired.
    """

    status: RepairDiagnosisStatus

    issues: list[RepairIssue] = Field(
        default_factory=list
    )

    blocking_reasons: list[str] = Field(
        default_factory=list
    )

    summary: str


class RepairResult(BaseModel):
    """
    Result of one property-repair invocation.

    repaired_property is present only when a new property
    was actually produced.
    """

    task_id: str

    status: RepairOutcomeStatus

    diagnosis: RepairDiagnosis

    repaired_property: GeneratedProperty | None = None

    metadata: dict = Field(
        default_factory=dict
    )