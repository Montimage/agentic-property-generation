from property_agent.assessment import (
    build_final_assessment,
)

from property_agent.models import (
    CompilationResult,
    CompilationStatus,
    FinalAssessmentStatus,
    GeneratedProperty,
    SemanticDimensionResult,
    SemanticReport,
    ValidationResult,
)


def aligned_dimension():
    return SemanticDimensionResult(
        score=1.0,
        justification="Aligned.",
        issues=[],
    )


def valid_semantic_report():
    return SemanticReport(
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


def valid_result(
    validator: str,
):
    return ValidationResult(
        validator=validator,
        valid=True,
        issues=[],
    )


def property_candidate():
    return GeneratedProperty(
        task_id="test_task",
        xml="<beginning></beginning>",
        model="fake/model",
        attempt=1,
    )


def compiled_result():
    return CompilationResult(
        status=CompilationStatus.COMPILED,
        compile_ok=True,
        returncode=0,
        local_xml_sha256="abc",
        remote_xml_sha256="abc",
        hash_matches=True,
        remote_duration_ms=100,
    )


def test_final_assessment_accepted():
    assessment = build_final_assessment(
        generated_property=(
            property_candidate()
        ),
        property_id="101",
        xml_validation=valid_result(
            "xml"
        ),
        syntax_validation=valid_result(
            "mmt_syntax"
        ),
        static_validation=valid_result(
            "mmt_static"
        ),
        semantic_report=(
            valid_semantic_report()
        ),
        compilation_result=(
            compiled_result()
        ),
    )

    assert (
        assessment.status
        == FinalAssessmentStatus.ACCEPTED
    )

    assert (
        assessment.statistics
        .local_compiler_agreement
        is True
    )


def test_compiler_rejection():
    compilation = CompilationResult(
        status=(
            CompilationStatus
            .COMPILATION_FAILED
        ),
        compile_ok=False,
        returncode=1,
        local_xml_sha256="abc",
        remote_xml_sha256="abc",
        hash_matches=True,
    )

    assessment = build_final_assessment(
        generated_property=(
            property_candidate()
        ),
        property_id="101",
        xml_validation=valid_result(
            "xml"
        ),
        syntax_validation=valid_result(
            "mmt_syntax"
        ),
        static_validation=valid_result(
            "mmt_static"
        ),
        semantic_report=(
            valid_semantic_report()
        ),
        compilation_result=compilation,
    )

    assert (
        assessment.status
        == FinalAssessmentStatus
        .REJECTED_COMPILATION
    )

    assert (
        assessment.statistics
        .local_compiler_agreement
        is False
    )


def test_endpoint_failure_is_inconclusive():
    compilation = CompilationResult(
        status=(
            CompilationStatus
            .ENDPOINT_ERROR
        ),
        compile_ok=None,
        local_xml_sha256="abc",
    )

    assessment = build_final_assessment(
        generated_property=(
            property_candidate()
        ),
        property_id="101",
        xml_validation=valid_result(
            "xml"
        ),
        syntax_validation=valid_result(
            "mmt_syntax"
        ),
        static_validation=valid_result(
            "mmt_static"
        ),
        semantic_report=(
            valid_semantic_report()
        ),
        compilation_result=compilation,
    )

    assert (
        assessment.status
        == FinalAssessmentStatus
        .INCONCLUSIVE
    )