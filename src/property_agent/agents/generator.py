import json

from lxml import etree

from property_agent.context import (
    GenerationContext,
    GenerationContextBuilder,
)

from property_agent.llm import LLMClient

from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    RetrievalResult,
)

from property_agent.retrieval import (
    VerifiedExampleRetriever,
)


class PropertyGenerationError(RuntimeError):
    """
    Raised when a candidate property cannot be produced
    correctly from the LLM output.
    """


def extract_mmt_xml(content: str) -> str:
    """
    Extract an MMT XML document from an LLM response.

    The model is instructed to return only XML, but this
    function tolerates accidental Markdown fences or short
    surrounding text.

    It does not perform full XML, MMT syntax, static, or
    semantic validation.
    """

    content = content.strip()

    start = content.find("<beginning")
    end_marker = "</beginning>"
    end = content.rfind(end_marker)

    if start == -1 or end == -1:
        raise PropertyGenerationError(
            "The LLM response does not contain a complete "
            "<beginning>...</beginning> MMT document."
        )

    end += len(end_marker)

    return content[start:end].strip()


def _check_property_id(
    xml: str,
    expected_property_id: str,
) -> None:
    """
    Verify that the generated property preserves the
    property_id supplied by the MonitoringTask.

    This is an input-output contract check, not a complete
    MMT validation step.
    """

    try:
        root = etree.fromstring(
            xml.encode("utf-8")
        )

    except etree.XMLSyntaxError as exc:
        raise PropertyGenerationError(
            "The generated property could not be parsed "
            "while checking the property_id. "
            f"XML parser error: {exc}"
        ) from exc

    properties = root.findall("property")

    if not properties:
        raise PropertyGenerationError(
            "The generated MMT document does not contain "
            "a property element."
        )

    actual_property_id = properties[0].get(
        "property_id"
    )

    if actual_property_id != expected_property_id:
        raise PropertyGenerationError(
            "The generated property_id does not match "
            "the property_id supplied by the monitoring "
            f"task. Expected '{expected_property_id}', "
            f"got '{actual_property_id}'."
        )


class PropertyGenerator:
    """
    Generate an MMT monitoring property from a
    MonitoringTask.
    """

    def __init__(
        self,
        client: LLMClient,
        context_builder: (
            GenerationContextBuilder | None
        ) = None,
        example_retriever: (
            VerifiedExampleRetriever | None
        ) = None,
    ):
        self.client = client

        self.context_builder = (
            context_builder
            or GenerationContextBuilder()
        )

        self.example_retriever = (
            example_retriever
            or VerifiedExampleRetriever()
        )

    def _format_protocol_knowledge_for_model(
        self,
        protocol_knowledge: dict[
            str,
            dict[str, object],
        ],
    ) -> dict[str, dict[str, object]]:
        """
        Reduce protocol knowledge to the information
        directly useful for property generation.

        Full DPI metadata remains available internally in
        the protocol knowledge repository.
        """

        formatted: dict[
            str,
            dict[str, object],
        ] = {}

        for protocol, knowledge in (
            protocol_knowledge.items()
        ):
            formatted[protocol] = {
                "protocol_id": (
                    knowledge.get(
                        "protocol_id"
                    )
                ),
                "protocol_name": (
                    knowledge.get(
                        "protocol_name"
                    )
                ),
                "attributes": [
                    {
                        "qualified_name": (
                            attribute.get(
                                "qualified_name"
                            )
                        ),
                        "security_c_type": (
                            attribute.get(
                                "security_c_type"
                            )
                        ),
                    }
                    for attribute in (
                        knowledge.get(
                            "attributes",
                            []
                        )
                    )
                ],
            }

        return formatted

    def _build_messages(
        self,
        task: MonitoringTask,
        context: GenerationContext,
    ) -> list[dict[str, str]]:
        """
        Construct stable model instructions plus
        task-specific context.

        Retrieved verified examples may be supplied as
        optional structural guidance when retrieval is
        enabled for the task.

        Authorized task assumptions are treated as part of
        the operative specification, while unresolved
        ambiguities must never be completed by invention.
        """

        retrieved_examples = (
            self._format_retrieved_examples(
                context
            )
        )

        model_protocol_knowledge = (
            self._format_protocol_knowledge_for_model(
                context.protocol_knowledge
            )
        )

        system_content = f"""
    You are an MMT monitoring-property generation agent.

    Your task is to convert a monitoring requirement into one MMT
    event-based XML property.

    Follow the supplied property-generation skill, property format,
    restrictions, and known-error guidance.

    Use only MMT constructs documented in the supplied property format.

    Do not invent protocol attributes.

    Use only protocol attributes provided in the task-specific protocol
    knowledge.

    When an event boolean_expression combines multiple conditions using
    logical operators, enclose the complete compound expression in an outer
    pair of parentheses.

    Because the property is XML, logical AND must always be XML-escaped.

    For example, inside a boolean_expression attribute, generate:

    ((condition_1) &amp;&amp; (condition_2))

    Never emit raw && inside an XML attribute.

    Similarly, XML-sensitive characters must always be escaped correctly.
    For example, use &lt; when a less-than comparison is required inside
    an XML attribute.

    Use exactly the property_id supplied in the monitoring task.

    Do not invent, replace, reinterpret, or modify the property_id.

    Preserve explicit task requirements, including numerical thresholds,
    timing constraints, ordering requirements, protocol requirements, and
    monitoring conditions.

    ====================
    XML OPERATORS VS. BOOLEAN OPERATORS
    ====================

    Do not confuse logical operators used inside `boolean_expression` with
    the `value` of an XML `<operator>` element.

    Use only XML `<operator>` values explicitly documented in the supplied
    MMT property format.

    Logical conjunction and disjunction belong inside `boolean_expression`.

    Do not generate `<operator value="AND">` or `<operator value="OR">` to
    represent boolean logic.

    ====================
    AUTHORIZED TASK ASSUMPTIONS
    ====================

    The monitoring task may contain an `assumptions` field.

    These assumptions are task-level design choices made only after the
    user explicitly authorized the system to resolve remaining
    task-level ambiguities.

    Treat authorized assumptions as part of the operative monitoring
    specification.

    Generate the property consistently with both:

    - explicit user requirements; and
    - authorized task assumptions.

    Do not replace, reinterpret, or modify an authorized assumption with a
    different assumption.

    Do not present an authorized assumption as a factual protocol semantic
    claim unless that fact is independently supported by the supplied
    protocol knowledge.

    An authorized task assumption does not permit you to invent:

    - unsupported protocol attributes;
    - procedure-code meanings;
    - message-code meanings;
    - undocumented state values;
    - factual protocol mappings absent from the supplied knowledge.

    ====================
    UNRESOLVED TASK AMBIGUITIES
    ====================

    The monitoring task may contain an `ambiguities` field.

    Every ambiguity still present in this field is unresolved.

    Do not resolve an unresolved ambiguity by inventing:

    - a numerical threshold;
    - a time duration;
    - a protocol value;
    - an attribute mapping;
    - a source identifier;
    - a correlation key;
    - a protocol semantic mapping;
    - any other missing monitoring condition.

    Generate only monitoring logic supported by the explicit task and the
    supplied knowledge.

    ====================
    SEMANTIC GROUNDING OF PROTOCOL VALUES
    ====================

    Protocol attribute availability and protocol semantics are separate concerns.

    Protocol attributes used in the generated property must exist in the
    supplied MMT protocol attribute knowledge.

    For the semantic meaning of protocol-specific values, you may use
    established protocol knowledge available to you as the language model.

    Do not invent a protocol-value-to-semantic-concept mapping merely because
    it would make the monitoring task easier to express.

    A concrete protocol value may be used when its semantic meaning is
    supported by at least one of:

    1. an explicit requirement in the current monitoring task;
    2. an authorized task assumption;
    3. established protocol-domain knowledge available to you.

    If you are uncertain about the semantic meaning of a concrete protocol
    value, do not fabricate the mapping.

    The existence of a protocol attribute establishes only that the field is
    observable through MMT. It does not by itself establish the meaning of a
    particular value.

    Retrieved property examples are structural guidance and must not be treated
    as the sole semantic justification for a protocol-value mapping.

    Task-defined operational mappings are authoritative. If the canonical task
    explicitly defines an identifier or attribute as the representation of an
    abstract concept such as "same source", follow that definition.

    ====================
    EMBEDDED FUNCTIONS
    ====================

    Prefer ordinary documented MMT property constructs when they are
    sufficient to represent the complete canonical monitoring requirement.

    If the task requires additional computation or state that cannot be
    adequately represented using ordinary documented MMT constructs, you may
    synthesize task-specific C logic using the documented embedded-function
    mechanism.

    When doing so:

    - follow the embedded-function structure and invocation rules supplied in the MMT property format and restrictions;
    - derive the C algorithm from the canonical monitoring requirements;
    - use only supplied protocol attributes as protocol-dependent inputs;
    - protocol attribute metadata may provide `security_c_type`;
    - when a protocol attribute is passed as an argument to an embedded function and `security_c_type` is known, use that C type for the corresponding function parameter;
    - do not infer another C parameter type when `security_c_type` is known;
    - if `security_c_type` is null, do not guess the embedded-function parameter type;
    - a null `security_c_type` does not mean that the attribute is unavailable; it means that its embedded-function C representation is not established by the supplied knowledge.
    - do not invent MMT APIs, helper functions, runtime facilities, libraries, lifecycle behavior, or property-language syntax;
    - do not substitute a count-like, time-like, or aggregate-like protocol attribute for required stateful computation unless its relevant semantics are actually established.

    The task-specific C algorithm itself may be newly synthesized using normal
    C programming logic.

    ====================
    RETRIEVED VERIFIED EXAMPLES
    ====================

    Retrieved verified examples, when supplied, are demonstrations of known
    MMT property structures and patterns.

    They are not authoritative sources of requirements for the current
    monitoring task.

    Do not copy from a retrieved example:

    - property identifiers;
    - numerical thresholds;
    - delay values;
    - protocol identifier values;
    - procedure or message values;
    - correlation attributes;
    - scenario-specific conditions;

    unless the same information is independently supported by:

    - the current monitoring task;
    - an authorized task assumption; or
    - the supplied protocol knowledge.

    Use retrieved examples only as structural guidance for expressing the
    current monitoring requirement.

    The current monitoring task, authorized assumptions, and supplied
    protocol knowledge always take precedence over retrieved examples.

    Return exactly one complete XML document beginning with <beginning>
    and ending with </beginning>.

    Do not include Markdown code fences or explanatory prose.

    ====================
    PROPERTY GENERATION SKILL
    ====================

    {context.generation_skill}

    ====================
    MMT PROPERTY FORMAT
    ====================

    {context.property_format}

    ====================
    GENERATION RESTRICTIONS
    ====================

    {context.restrictions}

    ====================
    KNOWN GENERATION ERRORS
    ====================

    {context.common_errors}
    """.strip()

        task_data = task.model_dump(
            mode="json"
        )

        user_content = f"""
    Generate one MMT monitoring property for the following monitoring task.

    ====================
    MONITORING TASK
    ====================

    {json.dumps(task_data, indent=2)}

    ====================
    EXPLICIT USER REQUIREMENTS
    ====================

    {json.dumps(task.requirements, indent=2)}

    ====================
    AUTHORIZED TASK ASSUMPTIONS
    ====================

    {json.dumps(task.assumptions, indent=2)}

    ====================
    UNRESOLVED TASK AMBIGUITIES
    ====================

    {json.dumps(task.ambiguities, indent=2)}

    ====================
    AVAILABLE MMT PROTOCOL KNOWLEDGE
    ====================

    {json.dumps(model_protocol_knowledge, indent=2)}

    ====================
    RETRIEVED VERIFIED PROPERTY EXAMPLES
    ====================

    {retrieved_examples}

    Use only the available protocol information and the MMT property
    constructs described in your instructions.

    Before using any concrete protocol-specific value, verify that its semantic meaning is supported by the monitoring task,
    an authorized assumption, or established protocol-domain knowledge.

    The supplied MMT protocol knowledge establishes attribute availability,
    not the semantic meaning of every protocol value.

    Do not use a retrieved example as the sole justification for a
    protocol-value-to-semantic-concept mapping.

    If verified examples were supplied, use them only as structural
    demonstrations.

    Explicit requirements and authorized assumptions together define the
    operative monitoring task.

    Any item still present in UNRESOLVED TASK AMBIGUITIES remains unresolved
    and must not be completed by invention.

    If verified examples were supplied, use them only as structural
    demonstrations. Do not transfer scenario-specific values or requirements
    from an example into the new property unless they are independently
    supported by the current task, an authorized assumption, or protocol
    knowledge.

    The generated property must use exactly this property identifier:

    {task.property_id}

    Do not substitute another identifier.

    Return only the complete XML property document.
    """.strip()

        return [
            {
                "role": "system",
                "content": system_content,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

    def generate(
        self,
        task: MonitoringTask,
        retrieval_result: RetrievalResult | None = None,
    ) -> GeneratedProperty:
        """
        Generate one MMT monitoring-property candidate.

        A precomputed RetrievalResult may be supplied by the
        orchestration workflow. When none is supplied, the
        generator performs retrieval itself for standalone use.
        """

        if retrieval_result is None:
            retrieval_result = (
                self.example_retriever.retrieve(
                    task
                )
            )

        context = self.context_builder.build(
            task,
            retrieval_result=(
                retrieval_result
            ),
        )

        messages = self._build_messages(
            task=task,
            context=context,
        )

        response = self.client.complete(
            messages
        )

        xml = extract_mmt_xml(
            response.content
        )

        _check_property_id(
            xml=xml,
            expected_property_id=(
                task.property_id
            ),
        )

        return GeneratedProperty(
            task_id=task.id,
            xml=xml,
            model=self.client.config.model,
            attempt=1,
            metadata={
                "provider_model":
                    response.model,

                "usage":
                    response.usage,

                "protocols":
                    task.protocols,

                "property_id":
                    task.property_id,

                "assumptions":
                    list(task.assumptions),

                "unresolved_ambiguities":
                    list(task.ambiguities),

                "retrieval": {
                    "enabled":
                        retrieval_result.enabled,

                    "used":
                        bool(
                            retrieval_result.examples
                        ),

                    "requested_k":
                        retrieval_result.requested_k,

                    "candidate_count":
                        retrieval_result.candidate_count,

                    "example_ids": [
                        example.property_id
                        for example
                        in retrieval_result.examples
                    ],

                    "scores": [
                        example.score
                        for example
                        in retrieval_result.examples
                    ],
                },
            },
        )

    def _format_retrieved_examples(
        self,
        context: GenerationContext,
    ) -> str:
        """
        Format retrieved verified examples for the initial
        generation prompt.
        """

        retrieval = (
            context.retrieval_result
        )

        if (
            retrieval is None
            or not retrieval.enabled
            or not retrieval.examples
        ):
            return (
                "No verified property examples "
                "were supplied for this task."
            )

        sections = []

        for example in retrieval.examples:

            metadata = {
                "property_id":
                    example.property_id,
                "property_type":
                    example.property_type,
                "description":
                    example.description,
                "protocols":
                    example.protocols,
                "tags":
                    example.tags,
                "constructs":
                    example.constructs,
                "retrieval_score":
                    example.score,
                "matched_protocols":
                    example.matched_protocols,
                "matched_terms":
                    example.matched_terms,
            }

            sections.append(
                "\n".join(
                    [
                        "EXAMPLE METADATA",
                        json.dumps(
                            metadata,
                            indent=2,
                        ),
                        "",
                        "VERIFIED XML",
                        example.xml,
                    ]
                )
            )

        return "\n\n".join(
            sections
        )