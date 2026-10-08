from property_agent.models import (
    SemanticAssessment,
    SemanticReport,
)


def build_semantic_report(
    assessment: SemanticAssessment,
) -> SemanticReport:
    """
    Convert an LLM-produced SemanticAssessment into
    a final SemanticReport.

    The overall score and acceptance decision are
    calculated deterministically and are not trusted
    to the LLM.
    """

    scores = [
        assessment.message_exchange_semantics.score,
        assessment.temporal_ordering_semantics.score,
        assessment.detection_semantics.score,
        assessment.attribute_relevance.score,
    ]

    overall_score = sum(scores) / len(scores)

    valid = all(
        score == 1.0
        for score in scores
    )

    return SemanticReport(
        message_exchange_semantics=(
            assessment.message_exchange_semantics
        ),
        temporal_ordering_semantics=(
            assessment.temporal_ordering_semantics
        ),
        detection_semantics=(
            assessment.detection_semantics
        ),
        attribute_relevance=(
            assessment.attribute_relevance
        ),
        overall_score=overall_score,
        valid=valid,
        summary=assessment.summary,
        recommendations=(
            assessment.recommendations
        ),
    )