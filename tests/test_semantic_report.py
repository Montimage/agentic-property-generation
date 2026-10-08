from property_agent.models import (
    SemanticAssessment,
    SemanticDimensionResult,
)

from property_agent.semantic import (
    build_semantic_report,
)


def aligned_dimension():
    return SemanticDimensionResult(
        score=1.0,
        justification="Aligned.",
        issues=[],
    )


def test_semantic_report_all_aligned():
    assessment = SemanticAssessment(
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
        summary="The property is aligned.",
        recommendations=[],
    )

    report = build_semantic_report(
        assessment
    )

    assert report.overall_score == 1.0
    assert report.valid is True


def test_semantic_report_failed_dimension():
    assessment = SemanticAssessment(
        message_exchange_semantics=(
            aligned_dimension()
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=(
            SemanticDimensionResult(
                score=0.0,
                justification=(
                    "Required detection logic "
                    "is missing."
                ),
                issues=[],
            )
        ),
        attribute_relevance=(
            aligned_dimension()
        ),
        summary="Detection logic is incomplete.",
        recommendations=[
            "Represent the required detection condition."
        ],
    )

    report = build_semantic_report(
        assessment
    )

    assert report.overall_score == 0.75
    assert report.valid is False


def test_semantic_report_uncertain_dimension():
    assessment = SemanticAssessment(
        message_exchange_semantics=(
            SemanticDimensionResult(
                score=0.5,
                justification=(
                    "Protocol semantic knowledge "
                    "is incomplete."
                ),
                issues=[],
            )
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
        summary=(
            "One semantic dimension remains "
            "uncertain."
        ),
        recommendations=[],
    )

    report = build_semantic_report(
        assessment
    )

    assert report.overall_score == 0.875
    assert report.valid is False