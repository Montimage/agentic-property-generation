from types import SimpleNamespace

import pytest

from property_agent.agents import (
    SemanticReviewError,
    SemanticReviewer,
    extract_json_object,
)

from property_agent.llm import (
    LLMResponse,
)

from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    SemanticIssueType,
)


class FakeSemanticLLMClient:
    """
    Fake semantic-review client.

    No real Ollama or external API request is made.
    """

    def __init__(
        self,
        content: str | None = None,
    ):
        self.config = SimpleNamespace(
            model="fake/semantic-model"
        )

        self.received_messages = None

        self.content = (
            content
            if content is not None
            else """
{
  "message_exchange_semantics": {
    "score": 0.5,
    "justification": "The task names registration-related requests, but the mapping from the generated NGAP procedure value to that behavior cannot be established with sufficient confidence.",
    "issues": [
      {
        "type": "knowledge_missing",
        "message": "The mapping between registration-related requests and the generated NGAP procedure code cannot be established with sufficient confidence.",
        "evidence": "ngap.procedure_code == 5"
      }
    ]
  },
  "temporal_ordering_semantics": {
    "score": 0.5,
    "justification": "The task requires a limited time window but does not define its duration.",
    "issues": [
      {
        "type": "task_underspecified",
        "message": "The duration of the limited time window is not specified by the monitoring task.",
        "evidence": null
      }
    ]
  },
  "detection_semantics": {
    "score": 0.5,
    "justification": "The task requests an abnormal number of requests but does not define the numerical threshold.",
    "issues": [
      {
        "type": "task_underspecified",
        "message": "The numerical threshold defining an abnormal number of registration-related requests is not specified.",
        "evidence": null
      }
    ]
  },
  "attribute_relevance": {
    "score": 0.5,
    "justification": "The task requires requests from the same source but does not define how source should be represented using available protocol attributes.",
    "issues": [
      {
        "type": "task_underspecified",
        "message": "The monitoring task does not define how the same source should be represented using available protocol attributes.",
        "evidence": null
      }
    ]
  },
  "summary": "The property cannot be fully verified because the task contains unresolved requirements and one protocol-semantic mapping cannot be established confidently.",
  "recommendations": [
    "Specify the numerical threshold defining an abnormal number of requests.",
    "Specify the duration of the limited time window.",
    "Clarify how the same source should be represented for this monitoring task."
  ]
}
"""
        )

    def complete(
        self,
        messages,
    ):
        self.received_messages = messages

        return LLMResponse(
            content=self.content,
            model="fake-semantic-model",
            usage={
                "prompt_tokens": 500,
                "completion_tokens": 250,
            },
        )


def make_task() -> MonitoringTask:
    return MonitoringTask(
        id="semantic_review_test",
        property_id="101",
        description=(
            "Detect an abnormal number of "
            "registration-related requests "
            "originating from the same source "
            "within a limited time window."
        ),
        protocols=[
            "ngap",
        ],
        requirements=[
            (
                "Detect an abnormal number of "
                "registration-related requests."
            ),
            (
                "The requests must originate "
                "from the same source."
            ),
            (
                "Evaluate the requests within "
                "a limited time window."
            ),
        ],
        ambiguities=[
            (
                "The numerical threshold that defines "
                "an abnormal number of "
                "registration-related requests is "
                "not specified."
            ),
            (
                "The duration of the limited time "
                "window is not specified."
            ),
            (
                "The task does not define how the "
                "same source should be represented "
                "using available protocol attributes."
            ),
        ],
    )


def make_task_with_explicit_source_mapping() -> MonitoringTask:
    """
    Fully specify the source-correlation representation
    so that the reviewer must treat it as an operative
    task-defined mapping.
    """

    return MonitoringTask(
        id="semantic_review_mapping_test",
        property_id="102",
        description=(
            "Detect more than 10 registration-related "
            "requests from the same source within "
            "5 seconds."
        ),
        protocols=[
            "ngap",
        ],
        requirements=[
            (
                "Detect more than 10 "
                "registration-related requests."
            ),
            (
                "Treat requests with the same AMF UE "
                "identifier as originating from the "
                "same source."
            ),
            (
                "Evaluate the requests within "
                "5 seconds."
            ),
        ],
        ambiguities=[],
    )


def make_property() -> GeneratedProperty:
    return GeneratedProperty(
        task_id="semantic_review_test",
        xml="""
<beginning>
    <property
        property_id="101"
        description="Example"
        type_property="SECURITY">

        <event
            value="COMPUTE"
            event_id="1"
            description="Registration request"
            boolean_expression="(ngap.procedure_code == 5)"/>

    </property>
</beginning>
""".strip(),
        model="fake/generator-model",
    )

def normalize_whitespace(
    value: str,
) -> str:
    """
    Normalize prompt whitespace so tests verify
    instruction content rather than formatting.
    """

    return " ".join(
        value.split()
    )

def test_extract_json_object():
    """
    Verify that JSON can be extracted from a response
    containing accidental Markdown formatting.
    """

    content = """
    Here is the assessment:

    ```json
    {
        "summary": "Example"
    }
    ```
    """

    result = extract_json_object(
        content
    )

    assert result.startswith("{")
    assert result.endswith("}")


def test_semantic_reviewer():
    """
    Verify that the structured LLM assessment is
    converted into the deterministic SemanticReport.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    report = reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    assert (
        report
        .message_exchange_semantics
        .score
        == 0.5
    )

    assert (
        report
        .temporal_ordering_semantics
        .score
        == 0.5
    )

    assert (
        report
        .detection_semantics
        .score
        == 0.5
    )

    assert (
        report
        .attribute_relevance
        .score
        == 0.5
    )

    assert report.overall_score == 0.5
    assert report.valid is False


def test_semantic_report_preserves_issue_types():
    """
    Verify that task underspecification and missing
    semantic knowledge remain distinguishable.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    report = reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    message_issue = (
        report
        .message_exchange_semantics
        .issues[0]
    )

    temporal_issue = (
        report
        .temporal_ordering_semantics
        .issues[0]
    )

    detection_issue = (
        report
        .detection_semantics
        .issues[0]
    )

    attribute_issue = (
        report
        .attribute_relevance
        .issues[0]
    )

    assert (
        message_issue.type
        == SemanticIssueType.KNOWLEDGE_MISSING
    )

    assert (
        temporal_issue.type
        == SemanticIssueType.TASK_UNDERSPECIFIED
    )

    assert (
        detection_issue.type
        == SemanticIssueType.TASK_UNDERSPECIFIED
    )

    assert (
        attribute_issue.type
        == SemanticIssueType.TASK_UNDERSPECIFIED
    )


def test_reviewer_receives_canonical_task_and_property():
    """
    Verify that the canonical monitoring task and
    generated XML are included in the review context.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert (
        "CURRENT CANONICAL MONITORING TASK"
        in user_message
    )

    assert (
        "abnormal number"
        in user_message
    )

    assert (
        "ngap.procedure_code == 5"
        in user_message
    )


def test_reviewer_receives_task_ambiguities_in_canonical_task():
    """
    Verify that structured task ambiguities are supplied
    to the semantic reviewer as part of the canonical
    monitoring task.
    """

    client = FakeSemanticLLMClient()

    task = make_task()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=task,
        generated_property=make_property(),
    )

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert (
        "CURRENT CANONICAL MONITORING TASK"
        in user_message
    )

    assert (
        '"ambiguities":'
        in user_message
    )

    for ambiguity in task.ambiguities:
        assert ambiguity in user_message


def test_reviewer_does_not_receive_historical_task_metadata():
    """
    Verify that semantic review receives the operative
    canonical task rather than historical provenance
    metadata that could conflict with refined
    requirements.
    """

    client = FakeSemanticLLMClient()

    task = make_task()

    historical_marker = (
        "HISTORICAL_PROVENANCE_ONLY_MARKER"
    )

    task = task.model_copy(
        update={
            "metadata": {
                "input": {
                    "original_text":
                        historical_marker
                }
            }
        }
    )

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=task,
        generated_property=make_property(),
    )

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert (
        "CURRENT CANONICAL MONITORING TASK"
        in user_message
    )

    assert (
        historical_marker
        not in user_message
    )

    for requirement in task.requirements:
        assert requirement in user_message

    for ambiguity in task.ambiguities:
        assert ambiguity in user_message

    for assumption in task.assumptions:
        assert assumption in user_message


def test_reviewer_system_prompt_contains_ambiguity_rules():
    """
    Verify that the reviewer receives the critical rules
    preventing unresolved task ambiguities from being
    completed by invention.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[0][
            "content"
        ]
    )

    assert (
        "EXPLICIT TASK AMBIGUITIES"
        in system_message
    )

    assert (
        "Do not treat an explicit task ambiguity "
        "as resolved"
        in system_message
    )

    assert (
        "Do not invent protocol attributes"
        in system_message
    )

    assert (
        "Use task_underspecified"
        in system_message
    )

    assert (
        "Use knowledge_missing"
        in system_message
    )


def test_reviewer_accepts_task_defined_operational_mappings():
    """
    Verify that an operational mapping explicitly
    defined by the canonical task is treated as
    authoritative for task conformance.
    """

    client = FakeSemanticLLMClient()

    task = (
        make_task_with_explicit_source_mapping()
    )

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=task,
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[0][
            "content"
        ]
    )

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    normalized_system_message = (
        normalize_whitespace(
            system_message
        )
    )

    normalized_user_message = (
        normalize_whitespace(
            user_message
        )
    )

    # The reviewer must recognize task-defined
    # operational mappings as authoritative.
    assert (
        "explicit task-defined operational mapping "
        "is authoritative for task conformance"
        in normalized_system_message.lower()
    )

    # The reviewer must not require independent
    # semantic evidence merely to confirm a mapping
    # that the canonical task explicitly defines.
    assert (
        "do not require independent "
        "protocol-semantic evidence"
        in normalized_system_message.lower()
    )

    # The explicit source-correlation mapping must
    # actually reach the reviewer as part of the
    # canonical monitoring task.
    assert (
        "treat requests with the same amf ue "
        "identifier as originating from the "
        "same source."
        in normalized_user_message.lower()
    )


def test_reviewer_may_use_established_protocol_domain_knowledge():
    """
    Verify that protocol semantics may be evaluated
    using established domain knowledge available to
    the reviewer LLM.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[0][
            "content"
        ]
    )

    normalized_system_message = (
        normalize_whitespace(
            system_message
        )
    )

    assert (
        "established protocol-domain knowledge "
        "available to you"
        in normalized_system_message
    )

    assert (
        "Do not report KNOWLEDGE_MISSING merely "
        "because no external protocol-semantic "
        "database was supplied"
        in normalized_system_message
    )


def test_reviewer_distinguishes_attribute_availability_from_semantics():
    """
    Verify that deterministic attribute availability
    and protocol semantic interpretation are treated
    as separate concerns.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[0][
            "content"
        ]
    )

    normalized_system_message = (
        normalize_whitespace(
            system_message
        )
    )

    assert (
        "PROTOCOL ATTRIBUTE AVAILABILITY VS. SEMANTICS"
        in system_message
    )

    assert (
        "The supplied MMT protocol attribute "
        "knowledge is authoritative"
        in normalized_system_message
    )

    assert (
        "The existence of an attribute does not "
        "by itself establish the semantic meaning"
        in normalized_system_message
    )


def test_reviewer_user_context_has_no_semantic_database_sections():
    """
    Verify that semantic review no longer depends on
    external protocol-semantic database fields.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert (
        "AVAILABLE MMT PROTOCOL ATTRIBUTE KNOWLEDGE"
        in user_message
    )

    assert (
        "PROTOCOLS WITHOUT ATTRIBUTE KNOWLEDGE"
        in user_message
    )

    assert (
        "AVAILABLE VERIFIED PROTOCOL SEMANTIC KNOWLEDGE"
        not in user_message
    )

    assert (
        "PROTOCOLS WITHOUT VERIFIED SEMANTIC KNOWLEDGE"
        not in user_message
    )

def test_reviewer_exposes_security_c_type_without_dpi_metadata():
    """
    Verify that semantic review receives the
    embedded-function C type for protocol attributes
    without unnecessary internal DPI metadata.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

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

def test_reviewer_checks_embedded_function_security_c_type():
    """
    Verify that known embedded-function parameter type
    mismatches are treated as property logic defects.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[
            0
        ]["content"]
    )

    normalized = (
        normalize_whitespace(
            system_message
        ).lower()
    )

    assert (
        "security_c_type"
        in normalized
    )

    assert (
        "property_logic_error"
        in normalized
    )

    assert (
        "detection semantics"
        in normalized
    )

    assert (
        "known mismatch is a property defect"
        in normalized
    )

def test_reviewer_does_not_guess_unknown_embedded_function_type():
    """
    Verify that an unknown embedded-function C
    representation is not guessed by the reviewer.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[
            0
        ]["content"]
    )

    normalized = (
        normalize_whitespace(
            system_message
        ).lower()
    )

    assert (
        "if `security_c_type` is null"
        in normalized
    )

    assert (
        "do not guess"
        in normalized
    )

    assert (
        "does not mean that the protocol attribute "
        "is unavailable"
        in normalized
    )

def test_reviewer_does_not_treat_examples_as_semantic_evidence():
    """
    Verify that property examples cannot be used as
    the sole justification for a protocol-semantic
    mapping.
    """

    client = FakeSemanticLLMClient()

    reviewer = SemanticReviewer(
        client=client
    )

    reviewer.review(
        task=make_task(),
        generated_property=make_property(),
    )

    system_message = (
        client.received_messages[0][
            "content"
        ]
    )

    assert (
        "a retrieved or example property"
        in system_message
    )

    assert (
        "Do not infer a semantic mapping solely"
        in system_message
    )


def test_invalid_semantic_json():
    """
    Verify that non-JSON semantic-review responses are
    rejected explicitly.
    """

    client = FakeSemanticLLMClient(
        content="This is not JSON."
    )

    reviewer = SemanticReviewer(
        client=client
    )

    with pytest.raises(
        SemanticReviewError
    ):
        reviewer.review(
            task=make_task(),
            generated_property=make_property(),
        )