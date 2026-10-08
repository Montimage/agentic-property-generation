from property_agent.models import (
    AssessmentStatistics,
    CompilationResult,
    CompilationStatus,
    FinalAssessmentStatus,
    FinalPropertyAssessment,
    GeneratedProperty,
    RepairOutcomeStatus,
    RepairResult,
    SemanticReport,
    ValidationResult,
    ValidationSeverity,
)


def _count_validation_issues(
    results: list[ValidationResult],
) -> tuple[int, int]:
    """
    Count deterministic validation errors and warnings.
    """

    errors = 0
    warnings = 0

    for result in results:
        for issue in result.issues:

            if (
                issue.severity
                == ValidationSeverity.ERROR
            ):
                errors += 1

            elif (
                issue.severity
                == ValidationSeverity.WARNING
            ):
                warnings += 1

    return errors, warnings


def _count_semantic_issues(
    report: SemanticReport | None,
) -> int:
    """
    Count structured semantic issues across all four
    semantic dimensions.
    """

    if report is None:
        return 0

    dimensions = [
        report.message_exchange_semantics,
        report.temporal_ordering_semantics,
        report.detection_semantics,
        report.attribute_relevance,
    ]

    return sum(
        len(
            dimension.issues
        )
        for dimension in dimensions
    )


def _local_compiler_agreement(
    *,
    local_valid: bool | None,
    compilation: CompilationResult | None,
) -> bool | None:
    """
    Compare local deterministic validity with the real
    MMT compilation outcome.

    Only compiler outcomes that actually establish a
    compilation result are compared.

    Infrastructure failures, timeouts, invalid remote
    responses, and missing compilation evidence do not
    produce an agreement value.
    """

    if (
        local_valid is None
        or compilation is None
    ):
        return None

    if (
        compilation.status
        == CompilationStatus.COMPILED
    ):
        compiler_valid = True

    elif (
        compilation.status
        == CompilationStatus.COMPILATION_FAILED
    ):
        compiler_valid = False

    else:
        return None

    return (
        local_valid
        == compiler_valid
    )


def build_final_assessment(
    *,
    generated_property: GeneratedProperty,
    property_id: str,
    xml_validation: ValidationResult | None,
    syntax_validation: ValidationResult | None,
    static_validation: ValidationResult | None,
    semantic_report: SemanticReport | None,
    compilation_result: CompilationResult | None,
    repair_result: RepairResult | None = None,
) -> FinalPropertyAssessment:
    """
    Build the deterministic final assessment for one
    generated MMT property.

    No LLM is used here.

    Deterministic validation may stop early. For example,
    when XML validation fails, syntax and static validation
    may not be executed. A known validation failure must
    therefore be distinguished from missing validation
    evidence.
    """

    # --------------------------------------------------------
    # Deterministic validation state
    # --------------------------------------------------------

    local_results = [
        xml_validation,
        syntax_validation,
        static_validation,
    ]

    deterministic_results = [
        result
        for result in local_results
        if result is not None
    ]

    error_count, warning_count = (
        _count_validation_issues(
            deterministic_results
        )
    )

    # A failure from any executed deterministic validator
    # is enough to establish local invalidity, even when
    # subsequent validators were intentionally skipped.
    known_local_failure = any(
        result is not None
        and result.valid is False
        for result in local_results
    )

    # All three results are required to establish a full
    # deterministic pass.
    all_local_results_present = all(
        result is not None
        for result in local_results
    )

    if known_local_failure:
        local_valid = False

    elif all_local_results_present:
        local_valid = all(
            result.valid
            for result in deterministic_results
        )

    else:
        local_valid = None

    # --------------------------------------------------------
    # Semantic statistics
    # --------------------------------------------------------

    semantic_issue_count = (
        _count_semantic_issues(
            semantic_report
        )
    )

    # This reflects the latest RepairResult supplied to the
    # assessment. The LangGraph workflow may later override
    # this aggregate statistic using its complete repair
    # history.
    repair_performed = (
        repair_result is not None
        and repair_result.status
        == RepairOutcomeStatus.REPAIRED
    )

    # --------------------------------------------------------
    # Experimental statistics
    # --------------------------------------------------------

    statistics = AssessmentStatistics(
        final_attempt=(
            generated_property.attempt
        ),
        deterministic_error_count=(
            error_count
        ),
        deterministic_warning_count=(
            warning_count
        ),
        semantic_issue_count=(
            semantic_issue_count
        ),
        semantic_overall_score=(
            semantic_report.overall_score
            if semantic_report is not None
            else None
        ),
        compilation_duration_ms=(
            compilation_result.remote_duration_ms
            if compilation_result is not None
            else None
        ),
        compilation_returncode=(
            compilation_result.returncode
            if compilation_result is not None
            else None
        ),
        local_compiler_agreement=(
            _local_compiler_agreement(
                local_valid=local_valid,
                compilation=compilation_result,
            )
        ),
        repair_performed=repair_performed,
    )

    reasons = []

    # --------------------------------------------------------
    # 1. Repair explicitly blocked
    # --------------------------------------------------------

    if (
        repair_result is not None
        and repair_result.status
        == RepairOutcomeStatus.BLOCKED
    ):
        reasons.extend(
            repair_result
            .diagnosis
            .blocking_reasons
        )

        if not reasons:
            reasons.append(
                "Automatic repair was blocked by "
                "the repair diagnosis."
            )

        return FinalPropertyAssessment(
            task_id=generated_property.task_id,
            property_id=property_id,
            status=FinalAssessmentStatus.BLOCKED,
            xml_valid=(
                xml_validation.valid
                if xml_validation is not None
                else None
            ),
            syntax_valid=(
                syntax_validation.valid
                if syntax_validation is not None
                else None
            ),
            static_valid=(
                static_validation.valid
                if static_validation is not None
                else None
            ),
            semantic_valid=(
                semantic_report.valid
                if semantic_report is not None
                else None
            ),
            semantic_score=(
                semantic_report.overall_score
                if semantic_report is not None
                else None
            ),
            compilation=compilation_result,
            statistics=statistics,
            reasons=reasons,
        )

    # --------------------------------------------------------
    # 2. Known deterministic validation failure
    # --------------------------------------------------------
    #
    # This check must occur before checking whether all
    # deterministic results are present.
    #
    # Example:
    #
    #   xml_validation.valid = False
    #   syntax_validation = None
    #   static_validation = None
    #
    # This is a known validation failure, not an
    # inconclusive assessment.
    # --------------------------------------------------------

    if known_local_failure:
        reasons.append(
            "The property failed deterministic "
            "validation."
        )

        final_status = (
            FinalAssessmentStatus
            .REJECTED_VALIDATION
        )

    # --------------------------------------------------------
    # 3. Deterministic evidence incomplete
    # --------------------------------------------------------

    elif not all_local_results_present:
        reasons.append(
            "One or more required deterministic "
            "validation results are missing."
        )

        final_status = (
            FinalAssessmentStatus.INCONCLUSIVE
        )

    # --------------------------------------------------------
    # 4. Semantic assessment missing
    # --------------------------------------------------------

    elif semantic_report is None:
        reasons.append(
            "Semantic validation was not performed."
        )

        final_status = (
            FinalAssessmentStatus.INCONCLUSIVE
        )

    # --------------------------------------------------------
    # 5. Semantic validation failure
    # --------------------------------------------------------

    elif not semantic_report.valid:
        reasons.append(
            "The property failed semantic validation."
        )

        final_status = (
            FinalAssessmentStatus
            .REJECTED_SEMANTIC
        )

    # --------------------------------------------------------
    # 6. Compilation evidence missing
    # --------------------------------------------------------

    elif compilation_result is None:
        reasons.append(
            "Remote MMT compilation was not performed."
        )

        final_status = (
            FinalAssessmentStatus.INCONCLUSIVE
        )

    # --------------------------------------------------------
    # 7. Real MMT compilation failure
    # --------------------------------------------------------

    elif (
        compilation_result.status
        == CompilationStatus.COMPILATION_FAILED
    ):
        reasons.append(
            "The real MMT compiler rejected "
            "the property."
        )

        final_status = (
            FinalAssessmentStatus
            .REJECTED_COMPILATION
        )

    # --------------------------------------------------------
    # 8. Successful final compilation
    # --------------------------------------------------------

    elif (
        compilation_result.status
        == CompilationStatus.COMPILED
        and compilation_result.compile_ok
        is True
    ):
        final_status = (
            FinalAssessmentStatus.ACCEPTED
        )

    # --------------------------------------------------------
    # 9. Infrastructure or inconclusive compilation result
    # --------------------------------------------------------

    else:
        reasons.append(
            "Remote MMT compilation did not produce "
            "a conclusive property result."
        )

        final_status = (
            FinalAssessmentStatus.INCONCLUSIVE
        )

    # --------------------------------------------------------
    # Final assessment
    # --------------------------------------------------------

    return FinalPropertyAssessment(
        task_id=generated_property.task_id,
        property_id=property_id,
        status=final_status,
        xml_valid=(
            xml_validation.valid
            if xml_validation is not None
            else None
        ),
        syntax_valid=(
            syntax_validation.valid
            if syntax_validation is not None
            else None
        ),
        static_valid=(
            static_validation.valid
            if static_validation is not None
            else None
        ),
        semantic_valid=(
            semantic_report.valid
            if semantic_report is not None
            else None
        ),
        semantic_score=(
            semantic_report.overall_score
            if semantic_report is not None
            else None
        ),
        compilation=compilation_result,
        statistics=statistics,
        reasons=reasons,
    )