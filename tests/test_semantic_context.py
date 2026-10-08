from property_agent.context import (
    SemanticReviewContextBuilder,
)

from property_agent.models import (
    MonitoringTask,
)


def test_build_semantic_context():
    task = MonitoringTask(
        id="semantic_test_001",
        property_id="301",
        description="Review an NGAP monitoring property.",
        protocols=["ngap"],
    )

    builder = (
        SemanticReviewContextBuilder()
    )

    context = builder.build(
        task
    )

    assert (
        "ngap"
        in context.protocol_attributes
    )

    assert (
        context.protocol_attributes[
            "ngap"
        ]["protocol_id"]
        == 903
    )

    assert (
        "Semantic Validation Skill"
        in context.validation_skill
    )


def test_semantic_context_tracks_knowledge():
    """
    Verify that semantic-review context tracks
    deterministic MMT protocol attribute knowledge
    without requiring a separate protocol-semantic
    database.
    """

    task = MonitoringTask(
        id="semantic_test_002",
        property_id="302",
        description=(
            "Review NGAP and NAS behavior."
        ),
        protocols=[
            "ngap",
            "nas_5g",
        ],
    )

    context = (
        SemanticReviewContextBuilder()
        .build(task)
    )

    assert set(
        context.protocol_attributes.keys()
    ) == {
        "ngap",
        "nas_5g",
    }

    assert isinstance(
        context.missing_attribute_knowledge,
        list,
    )

    assert (
        context.missing_attribute_knowledge
        == []
    )

    # Semantic interpretation is intentionally
    # delegated to the reviewer LLM rather than a
    # separate per-protocol semantic database.
    assert not hasattr(
        context,
        "protocol_semantics",
    )

    assert not hasattr(
        context,
        "missing_semantic_knowledge",
    )