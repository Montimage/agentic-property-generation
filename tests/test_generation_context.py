import pytest

from property_agent.context import (
    GenerationContextBuilder,
    MissingProtocolKnowledgeError,
)

from property_agent.models import (
    MonitoringTask,
)


def test_build_ngap_context():
    task = MonitoringTask(
        id="test_001",
        property_id="201",
        description="Test NGAP monitoring task.",
        protocols=["ngap"],
    )

    builder = GenerationContextBuilder()

    context = builder.build(task)

    assert "ngap" in context.protocol_knowledge

    assert (
        context.protocol_knowledge[
            "ngap"
        ]["protocol_id"]
        == 903
    )

    assert (
        "MMT Property Generation Skill"
        in context.generation_skill
    )

    assert (
        "MMT Event-Based Property Format"
        in context.property_format
    )

def test_protocol_attribute_type_metadata_is_loaded():
    task = MonitoringTask(
        id="test_005",
        property_id="205",
        description="NGAP type metadata test.",
        protocols=["ngap"],
    )

    context = (
        GenerationContextBuilder()
        .build(task)
    )

    attributes = (
        context.protocol_knowledge[
            "ngap"
        ]["attributes"]
    )

    amf_ue_id = next(
        attribute
        for attribute in attributes
        if attribute["name"]
        == "amf_ue_id"
    )

    assert (
        amf_ue_id["qualified_name"]
        == "ngap.amf_ue_id"
    )

    assert (
        amf_ue_id["dpi_type"]
        == "MMT_U64_DATA"
    )

    assert (
        amf_ue_id["data_len"]
        == 8
    )

    assert (
        amf_ue_id[
            "security_c_type"
        ]
        == "double"
    )

def test_unknown_security_c_type_is_loaded():
    task = MonitoringTask(
        id="test_006",
        property_id="206",
        description="NGAP unknown type test.",
        protocols=["ngap"],
    )

    context = (
        GenerationContextBuilder()
        .build(task)
    )

    attributes = (
        context.protocol_knowledge[
            "ngap"
        ]["attributes"]
    )

    p_payload = next(
        attribute
        for attribute in attributes
        if attribute["name"]
        == "p_payload"
    )

    assert (
        p_payload[
            "security_c_type"
        ]
        is None
    )

def test_only_required_protocols_are_loaded():
    task = MonitoringTask(
        id="test_002",
        property_id="202",
        description="NGAP and NAS monitoring.",
        protocols=[
            "ngap",
            "nas_5g",
        ],
    )

    context = (
        GenerationContextBuilder()
        .build(task)
    )

    assert set(
        context.protocol_knowledge.keys()
    ) == {
        "ngap",
        "nas_5g",
    }


def test_missing_protocol_knowledge():
    task = MonitoringTask(
        id="test_003",
        property_id="203",
        description="Unknown protocol.",
        protocols=[
            "unknown_protocol"
        ],
    )

    builder = GenerationContextBuilder()

    with pytest.raises(
        MissingProtocolKnowledgeError
    ):
        builder.build(task)


def test_property_id_does_not_affect_context_loading():
    """
    Verify that property_id belongs to the monitoring task
    but does not change which protocol knowledge is loaded.
    """

    task = MonitoringTask(
        id="test_004",
        property_id="204",
        description="NGAP monitoring task.",
        protocols=["ngap"],
    )

    context = (
        GenerationContextBuilder()
        .build(task)
    )

    assert set(
        context.protocol_knowledge.keys()
    ) == {"ngap"}

    assert task.property_id == "204"