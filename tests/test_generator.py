from types import SimpleNamespace

import pytest

from property_agent.agents import (
    PropertyGenerationError,
    PropertyGenerator,
    extract_mmt_xml,
)

from property_agent.llm import (
    LLMResponse,
)

from property_agent.models import (
    MonitoringTask,
    RetrievalResult,
    RetrievedExample,
)


class FakeLLMClient:
    """
    Fake LLM client used to test property generation
    without contacting a real model.
    """

    def __init__(
        self,
        property_id: str = "101",
    ):
        self.config = SimpleNamespace(
            model="fake/test-model"
        )

        self.property_id = property_id
        self.received_messages = None

    def complete(self, messages):
        """
        Store the messages received by the fake client
        and return a deterministic MMT property.
        """

        self.received_messages = messages

        return LLMResponse(
            content=f"""
        ```xml
        <beginning>
            <property
                value="COMPUTE"
                property_id="{self.property_id}"
                description="Example"
                type_property="SECURITY">

                <event
                    value="COMPUTE"
                    event_id="1"
                    description="Example event"
                    boolean_expression="ngap.procedure_code == 4"/>

            </property>
        </beginning>
        """,
        model="fake-provider-model",
        usage={
        "prompt_tokens": 100,
        "completion_tokens": 50,
        },
        )

def make_task() -> MonitoringTask:
    """
    Create a reusable monitoring task for generator tests.
    """
    return MonitoringTask(
        id="ngap_test",
        property_id="101",
        description=(
            "Detect a 5G authentication-related "
            "monitoring condition."
        ),
        protocols=[
            "ngap",
        ],
        requirements=[
            "Use the available NGAP protocol information."
        ],
    )

def test_extract_mmt_xml():
    """
    Verify that XML can be extracted from an LLM response
    containing surrounding text or Markdown formatting.
    """
    content = """
    Here is the property you requested:
    <beginning>
        <property></property>
    </beginning>
    """
    xml = extract_mmt_xml(content)

    assert xml.startswith("<beginning>")
    assert xml.endswith("</beginning>")

def test_generate_property():
    """
    Verify that PropertyGenerator returns a GeneratedProperty
    using the fake LLM client.
    """
    task = MonitoringTask(
    id="ngap_test",
    property_id="101",
    description="Monitor an NGAP procedure.",
    protocols=["ngap"],
    requirements=[
        "Use the NGAP procedure code."
    ],
    )

    client = FakeLLMClient(
        property_id="101"
    )

    generator = PropertyGenerator(
        client=client
    )

    result = generator.generate(task)

    assert result.task_id == "ngap_test"

    assert result.model == "fake/test-model"

    assert result.attempt == 1

    assert result.xml.startswith(
        "<beginning>"
    )

    assert result.xml.endswith(
        "</beginning>"
    )

    assert (
        'property_id="101"'
        in result.xml
    )

    assert (
        "ngap.procedure_code"
        in result.xml
    )

    assert (
        result.metadata["property_id"]
        == "101"
    )

def test_generator_receives_protocol_knowledge():
    """
    Verify that the generator receives only the protocol
    knowledge required by the task.
    """
    task = MonitoringTask(
    id="knowledge_test",
    property_id="102",
    description="NGAP monitoring task.",
    protocols=["ngap"],
    )

    client = FakeLLMClient(
        property_id="102"
    )

    generator = PropertyGenerator(
        client=client
    )

    generator.generate(task)

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert (
        "ngap.procedure_code"
        in user_message
    )

    assert (
        "http2.header_method"
        not in user_message
    )

def test_generator_exposes_security_c_type_without_dpi_metadata():
    """
    Verify that the LLM receives the embedded-function
    C type for protocol attributes without unnecessary
    internal DPI metadata.
    """
    task = MonitoringTask(
        id="type_metadata_test",
        property_id="105",
        description="NGAP monitoring task.",
        protocols=["ngap"],
    )

    client = FakeLLMClient(
        property_id="105"
    )

    generator = PropertyGenerator(
        client=client
    )

    generator.generate(task)

    user_message = (
        client.received_messages[
            1
        ]["content"]
    )

    assert (
        '"qualified_name": "ngap.amf_ue_id"'
        in user_message
    )

    assert (
        '"security_c_type": "double"'
        in user_message
    )

    assert (
        '"qualified_name": "ngap.p_payload"'
        in user_message
    )

    assert (
        '"security_c_type": null'
        in user_message
    )

    assert (
        '"dpi_type"'
        not in user_message
    )

    assert (
        '"data_len"'
        not in user_message
    )

def test_generator_includes_property_id_in_task_context():
    """
    Verify that the requested property identifier is
    explicitly provided to the LLM.
    """
    task = MonitoringTask(
    id="property_id_test",
    property_id="103",
    description="NGAP monitoring task.",
    protocols=["ngap"],
    )

    client = FakeLLMClient(
        property_id="103"
    )

    generator = PropertyGenerator(
        client=client
    )

    generator.generate(task)

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert '"property_id": "103"' in user_message

    assert (
        "The generated property must use "
        "exactly this property identifier"
        in user_message
    )

def test_generator_rejects_changed_property_id():
    """
    Verify that generation fails when the LLM replaces
    the property_id supplied by the task.
    """
    task = MonitoringTask(
    id="wrong_property_id_test",
    property_id="104",
    description="NGAP monitoring task.",
    protocols=["ngap"],
    )

    # Simulate an LLM that incorrectly returns
    # a different property identifier.
    client = FakeLLMClient(
        property_id="91"
    )

    generator = PropertyGenerator(
        client=client
    )

    with pytest.raises(
        PropertyGenerationError,
        match="property_id",
    ):
        generator.generate(task)

class FakeExampleRetriever:
    def retrieve(
        self,
        task,
    ):
        return RetrievalResult(
            task_id=task.id,
            enabled=True,
            requested_k=2,
            candidate_count=1,
            examples=[
                RetrievedExample(
                    property_id="91",
                    file=(
                        "properties/"
                        "ngap_authentication_hijack_91.xml"
                    ),
                    property_type="ATTACK",
                    description=(
                        "Verified NGAP "
                        "authentication example."
                    ),
                    protocols=[
                        "ngap",
                        "nas_5g",
                        "sctp_data",
                    ],
                    tags=[
                        "authentication",
                    ],
                    constructs=[
                        "multiple_events",
                    ],
                    score=0.8,
                    matched_protocols=[
                        "ngap",
                    ],
                    matched_terms=[
                        "authentication",
                    ],
                    matched_tags=[
                        "authentication",
                    ],
                    xml="""
<beginning>
    <property
        value="THEN"
        property_id="91"
        description="Verified example"
        type_property="ATTACK">
    </property>
</beginning>
""".strip(),
                )
            ],
        )

def test_generator_receives_retrieved_example():
    client = FakeLLMClient(
        property_id="101"
    )

    generator = PropertyGenerator(
        client=client,
        example_retriever=(
            FakeExampleRetriever()
        ),
    )

    result = generator.generate(
        make_task()
    )

    user_message = (
        client.received_messages[
            1
        ]["content"]
    )

    assert (
        "RETRIEVED VERIFIED "
        "PROPERTY EXAMPLES"
        in user_message
    )

    assert (
        'property_id="91"'
        in user_message
    )

    assert (
        result.metadata[
            "retrieval"
        ]["used"]
        is True
    )

    assert (
        result.metadata[
            "retrieval"
        ]["example_ids"]
        == ["91"]
    )

def test_generator_keeps_task_property_id_with_retrieval():
    client = FakeLLMClient(
        property_id="101"
    )

    generator = PropertyGenerator(
        client=client,
        example_retriever=(
            FakeExampleRetriever()
        ),
    )

    result = generator.generate(
        make_task()
    )

    assert (
        'property_id="101"'
        in result.xml
    )

    assert (
        result.metadata[
            "property_id"
        ]
        == "101"
    )

def test_generator_receives_authorized_assumptions():
    task = make_task().model_copy(
        update={
            "assumptions": [
                (
                    "Treat requests sharing the same "
                    "AMF UE identifier as originating "
                    "from the same source."
                )
            ]
        }
    )

    client = FakeLLMClient()

    generator = PropertyGenerator(
        client=client
    )

    generator.generate(
        task
    )

    user_message = (
        client.received_messages[
            1
        ]["content"]
    )

    assert (
        "AUTHORIZED TASK ASSUMPTIONS"
        in user_message
    )

    assert (
        "same AMF UE identifier"
        in user_message
    )

def test_generator_does_not_treat_assumptions_as_protocol_facts():
    task = make_task().model_copy(
        update={
            "assumptions": [
                "Use a 5-second time window."
            ]
        }
    )

    client = FakeLLMClient()

    generator = PropertyGenerator(
        client=client
    )

    generator.generate(
        task
    )

    system_message = (
        client.received_messages[
            0
        ]["content"]
    )

    assert (
        "authorized task assumption does not permit"
        in system_message.lower()
    )

    assert (
        "procedure-code meanings"
        in system_message
    )