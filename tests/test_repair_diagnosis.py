from property_agent.models import (
    RepairDiagnosisStatus,
    SemanticDimensionResult,
    SemanticIssue,
    SemanticIssueType,
    SemanticReport,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

from property_agent.repair import (
    build_repair_diagnosis,
)


def aligned_dimension():
    return SemanticDimensionResult(
        score=1.0,
        justification="Aligned.",
        issues=[],
    )


def test_syntax_error_is_repairable():
    validation = ValidationResult(
        validator="mmt_syntax",
        valid=False,
        issues=[
            ValidationIssue(
                code=(
                    "INVALID_COMPUTE_EVENT_COUNT"
                ),
                message=(
                    "A COMPUTE property must "
                    "contain exactly one event."
                ),
                severity=(
                    ValidationSeverity.ERROR
                ),
            )
        ],
    )

    diagnosis = build_repair_diagnosis(
        validation_results=[
            validation
        ]
    )

    assert (
        diagnosis.status
        == RepairDiagnosisStatus.REPAIRABLE
    )

    assert (
        diagnosis.issues[0].code
        == "INVALID_COMPUTE_EVENT_COUNT"
    )

    assert (
        diagnosis.issues[0].repairable
        is True
    )


def test_task_underspecified_blocks_repair():
    detection = SemanticDimensionResult(
        score=0.5,
        justification=(
            "The abnormal-request criterion "
            "is not quantitatively defined."
        ),
        issues=[
            SemanticIssue(
                type=(
                    SemanticIssueType
                    .TASK_UNDERSPECIFIED
                ),
                message=(
                    "The task does not define "
                    "what constitutes an abnormal "
                    "number of requests."
                ),
                evidence=(
                    "Task: abnormal number "
                    "of requests."
                ),
            )
        ],
    )

    report = SemanticReport(
        message_exchange_semantics=(
            aligned_dimension()
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=detection,
        attribute_relevance=(
            aligned_dimension()
        ),
        overall_score=0.875,
        valid=False,
        summary=(
            "The task is underspecified."
        ),
        recommendations=[],
    )

    diagnosis = build_repair_diagnosis(
        validation_results=[],
        semantic_report=report,
    )

    assert (
        diagnosis.status
        == RepairDiagnosisStatus.BLOCKED
    )

    assert len(
        diagnosis.blocking_reasons
    ) == 1

    assert (
        diagnosis.issues[0].blocking
        is True
    )


def test_missing_knowledge_blocks_repair():
    protocol_semantics = (
        SemanticDimensionResult(
            score=0.5,
            justification=(
                "Procedure-code semantics "
                "cannot be verified."
            ),
            issues=[
                SemanticIssue(
                    type=(
                        SemanticIssueType
                        .KNOWLEDGE_MISSING
                    ),
                    message=(
                        "The supplied knowledge "
                        "does not establish the "
                        "meaning of procedure_code 5."
                    ),
                    evidence=(
                        "ngap.procedure_code == 5"
                    ),
                )
            ],
        )
    )

    report = SemanticReport(
        message_exchange_semantics=(
            protocol_semantics
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=(
            aligned_dimension()
        ),
        attribute_relevance=(
            aligned_dimension()
        ),
        overall_score=0.875,
        valid=False,
        summary=(
            "Protocol semantics are uncertain."
        ),
        recommendations=[],
    )

    diagnosis = build_repair_diagnosis(
        validation_results=[],
        semantic_report=report,
    )

    assert (
        diagnosis.status
        == RepairDiagnosisStatus.BLOCKED
    )


def test_no_issues_requires_no_repair():
    report = SemanticReport(
        message_exchange_semantics=(
            aligned_dimension()
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=(
            aligned_dimension()
        ),
        attribute_relevance=(
            aligned_dimension()
        ),
        overall_score=1.0,
        valid=True,
        summary="Aligned.",
        recommendations=[],
    )

    validation = ValidationResult(
        validator="mmt_syntax",
        valid=True,
        issues=[],
    )

    diagnosis = build_repair_diagnosis(
        validation_results=[
            validation
        ],
        semantic_report=report,
    )

    assert (
        diagnosis.status
        == RepairDiagnosisStatus.NO_REPAIR_NEEDED
    )

    assert diagnosis.issues == []