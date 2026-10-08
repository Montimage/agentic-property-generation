import json

from property_agent.models import (
    RepairDiagnosis,
    RepairDiagnosisStatus,
    RepairIssue,
    RepairIssueSource,
    SemanticIssueType,
    SemanticReport,
    ValidationResult,
    ValidationSeverity,
)


BLOCKING_SEMANTIC_TYPES = {
    SemanticIssueType.KNOWLEDGE_MISSING,
    SemanticIssueType.TASK_UNDERSPECIFIED,
}


VALIDATOR_SOURCE_MAP = {
    "xml": RepairIssueSource.XML,
    "mmt_syntax": RepairIssueSource.MMT_SYNTAX,
    "mmt_static": RepairIssueSource.MMT_STATIC,
}


def _source_from_validator(
    validator: str,
) -> RepairIssueSource:
    """
    Map validator names to normalized repair sources.
    """

    return VALIDATOR_SOURCE_MAP.get(
        validator,
        RepairIssueSource.OTHER,
    )


def _context_to_evidence(
    context: dict,
) -> str | None:
    """
    Convert deterministic validation context into a
    compact evidence string.
    """

    if not context:
        return None

    return json.dumps(
        context,
        sort_keys=True,
    )


def _add_deterministic_issues(
    validation_results: list[ValidationResult],
) -> list[RepairIssue]:
    """
    Normalize deterministic validation errors.

    Normal warnings are not treated as repair requests.

    Missing protocol knowledge is treated as blocking
    because repairing the affected protocol reference
    without knowledge could introduce unsupported facts.
    """

    repair_issues = []

    for result in validation_results:
        source = _source_from_validator(
            result.validator
        )

        relevant_count = 0

        for issue in result.issues:

            knowledge_missing = (
                issue.code
                == "PROTOCOL_KNOWLEDGE_MISSING"
            )

            if (
                issue.severity
                != ValidationSeverity.ERROR
                and not knowledge_missing
            ):
                continue

            blocking = knowledge_missing
            repairable = not blocking

            repair_issues.append(
                RepairIssue(
                    source=source,
                    code=issue.code,
                    message=issue.message,
                    evidence=_context_to_evidence(
                        issue.context
                    ),
                    repairable=repairable,
                    blocking=blocking,
                )
            )

            relevant_count += 1

        if (
            result.valid is False
            and relevant_count == 0
        ):
            repair_issues.append(
                RepairIssue(
                    source=source,
                    code="VALIDATION_FAILED",
                    message=(
                        f"Validator '{result.validator}' "
                        "reported failure without an "
                        "actionable error."
                    ),
                    evidence=None,
                    repairable=False,
                    blocking=True,
                )
            )

    return repair_issues


def _add_semantic_issues(
    semantic_report: SemanticReport | None,
) -> list[RepairIssue]:
    """
    Normalize issues reported by the semantic reviewer.
    """

    if semantic_report is None:
        return []

    repair_issues = []

    dimensions = {
        "message_exchange_semantics": (
            semantic_report.message_exchange_semantics
        ),
        "temporal_ordering_semantics": (
            semantic_report.temporal_ordering_semantics
        ),
        "detection_semantics": (
            semantic_report.detection_semantics
        ),
        "attribute_relevance": (
            semantic_report.attribute_relevance
        ),
    }

    for dimension_name, dimension in dimensions.items():

        for issue in dimension.issues:

            blocking = (
                issue.type
                in BLOCKING_SEMANTIC_TYPES
            )

            repair_issues.append(
                RepairIssue(
                    source=(
                        RepairIssueSource.SEMANTIC
                    ),
                    code=issue.type.value.upper(),
                    message=issue.message,
                    evidence=(
                        issue.evidence
                        or dimension_name
                    ),
                    repairable=not blocking,
                    blocking=blocking,
                )
            )

        # A score below 1.0 should normally contain
        # at least one structured issue. If it does not,
        # do not ask the repair agent to guess what is wrong.
        if (
            dimension.score < 1.0
            and not dimension.issues
        ):
            repair_issues.append(
                RepairIssue(
                    source=(
                        RepairIssueSource.SEMANTIC
                    ),
                    code=(
                        "SEMANTIC_REVIEW_INCOMPLETE"
                    ),
                    message=(
                        f"Semantic dimension "
                        f"'{dimension_name}' received "
                        f"score {dimension.score}, but "
                        "no actionable issue was "
                        "provided."
                    ),
                    evidence=dimension.justification,
                    repairable=False,
                    blocking=True,
                )
            )

    return repair_issues


def build_repair_diagnosis(
    validation_results: list[ValidationResult],
    semantic_report: SemanticReport | None = None,
) -> RepairDiagnosis:
    """
    Build a deterministic diagnosis from validation
    results and semantic feedback.

    This function does not use an LLM.
    """

    issues = []

    issues.extend(
        _add_deterministic_issues(
            validation_results
        )
    )

    issues.extend(
        _add_semantic_issues(
            semantic_report
        )
    )

    if not issues:
        return RepairDiagnosis(
            status=(
                RepairDiagnosisStatus.NO_REPAIR_NEEDED
            ),
            issues=[],
            blocking_reasons=[],
            summary=(
                "No repairable or blocking issues "
                "were identified."
            ),
        )

    blocking_reasons = [
        issue.message
        for issue in issues
        if issue.blocking
    ]

    # Remove duplicates while preserving order.
    blocking_reasons = list(
        dict.fromkeys(
            blocking_reasons
        )
    )

    if blocking_reasons:
        return RepairDiagnosis(
            status=RepairDiagnosisStatus.BLOCKED,
            issues=issues,
            blocking_reasons=blocking_reasons,
            summary=(
                "Automatic repair is blocked because "
                "required information is missing or "
                "the available diagnosis is not "
                "sufficiently actionable."
            ),
        )

    return RepairDiagnosis(
        status=RepairDiagnosisStatus.REPAIRABLE,
        issues=issues,
        blocking_reasons=[],
        summary=(
            "The identified issues can be supplied "
            "to the property repair agent."
        ),
    )