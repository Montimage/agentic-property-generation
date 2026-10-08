import json

from lxml import etree

from property_agent.context import (
    RepairContext,
    RepairContextBuilder,
)

from property_agent.llm import (
    LLMClient,
)

from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    RepairDiagnosis,
    RepairDiagnosisStatus,
    RepairOutcomeStatus,
    RepairResult,
    SemanticReport,
)

from .generator import (
    PropertyGenerationError,
    extract_mmt_xml,
)


class PropertyRepairError(RuntimeError):
    """
    Raised when a requested property repair cannot be
    converted into a valid repair candidate.
    """


def _check_repaired_property_id(
    xml: str,
    expected_property_id: str,
) -> None:
    """
    Verify that repair did not modify the immutable
    property identifier.
    """

    try:
        root = etree.fromstring(
            xml.encode("utf-8")
        )

    except etree.XMLSyntaxError as exc:
        raise PropertyRepairError(
            "The repaired property could not be parsed "
            "while checking the property_id."
        ) from exc

    properties = root.findall(
        "property"
    )

    if not properties:
        raise PropertyRepairError(
            "The repaired MMT document does not contain "
            "a property element."
        )

    actual_property_id = properties[
        0
    ].get("property_id")

    if (
        actual_property_id
        != expected_property_id
    ):
        raise PropertyRepairError(
            "The repair changed the immutable "
            f"property_id. Expected "
            f"'{expected_property_id}', got "
            f"'{actual_property_id}'."
        )


class PropertyRepairer:
    """
    Repair one generated MMT property using explicit
    deterministic and semantic diagnosis.

    One invocation performs at most one LLM repair.
    """

    def __init__(
        self,
        client: LLMClient,
        context_builder: (
            RepairContextBuilder | None
        ) = None,
    ):
        self.client = client

        self.context_builder = (
            context_builder
            or RepairContextBuilder()
        )

    def _format_protocol_attributes_for_model(
        self,
        protocol_attributes: dict[
            str,
            dict[str, object],
        ],
    ) -> dict[str, dict[str, object]]:
        """
        Reduce protocol attribute knowledge to the
        information directly useful for property repair.

        Full DPI metadata remains available internally.
        """

        formatted: dict[
            str,
            dict[str, object],
        ] = {}

        for protocol, knowledge in (
            protocol_attributes.items()
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
        current_property: GeneratedProperty,
        diagnosis: RepairDiagnosis,
        context: RepairContext,
        semantic_report: (
            SemanticReport | None
        ) = None,
    ) -> list[dict[str, str]]:
        """
        Build repair instructions and task-specific evidence.

        Structured diagnosis is authoritative for the
        repair scope.

        Semantic recommendations are supplementary.

        MMT protocol attribute availability is grounded
        in deterministic local knowledge, while factual
        protocol semantics may be interpreted using
        established protocol-domain knowledge available
        to the LLM.
        """

        semantic_data = (
            semantic_report.model_dump(
                mode="json"
            )
            if semantic_report is not None
            else None
        )

        model_protocol_attributes = (
            self._format_protocol_attributes_for_model(
                context.protocol_attributes
            )
        )

        operative_task_data = {
            "id": task.id,
            "property_id": task.property_id,
            "protocols": list(
                task.protocols
            ),
            "monitoring_point":
                task.monitoring_point,
            "requirements": list(
                task.requirements
            ),
            "restrictions": list(
                task.restrictions
            ),
            "expected_behavior":
                task.expected_behavior,
            "ambiguities": list(
                task.ambiguities
            ),
            "assumptions": list(
                task.assumptions
            ),
        }

        system_content = f"""
    You are an MMT monitoring-property repair agent.

    Your responsibility is to repair an existing generated property using the
    supplied structured repair diagnosis.

    You are not performing unrestricted initial property generation.

    Preserve every part of the current property that is already correct.

    Make the smallest changes necessary to address the diagnosed repairable
    issues.

    ====================
    CANONICAL TASK AUTHORITY
    ====================

    The CURRENT CANONICAL MONITORING TASK is authoritative.

    Preserve its:

    - requirements;
    - restrictions;
    - authorized assumptions;
    - unresolved ambiguities;
    - property identifier.

    Do not reinterpret the canonical task using historical wording.

    Do not invent missing task requirements.

    If the canonical task explicitly defines an operational mapping, such as
    using a particular observable identifier to represent "same source", that
    mapping is authoritative for repair.

    Do not replace an explicit task-defined mapping with another technically
    plausible representation.

    Use exactly the property_id supplied by the canonical monitoring task.

    Never change the property_id.

    ====================
    PROTOCOL ATTRIBUTE AVAILABILITY VS. SEMANTICS
    ====================

    Protocol attribute availability and protocol semantic meaning are separate
    concerns.

    The supplied MMT protocol attribute knowledge is authoritative for whether
    an attribute is exposed by the monitored MMT implementation.

    Do not introduce protocol attributes that are absent from the supplied MMT
    protocol attribute knowledge.

    For factual protocol semantics, you may use:

    1. the CURRENT CANONICAL MONITORING TASK;
    2. authorized task assumptions;
    3. established protocol-domain knowledge available to you as the language
    model.

    Do not fabricate a protocol-semantic mapping when you cannot establish it
    with sufficient confidence.

    The existence of an attribute does not by itself establish the meaning of a
    particular value of that attribute.

    For example, knowing that:

    <protocol>.<attribute>

    exists does not by itself establish what:

    <protocol>.<attribute> == <value>

    means.

    A task-defined operational mapping is different from a factual
    protocol-value-to-semantic-concept mapping.

    If the task explicitly defines a correlation representation, preserve it.

    If the repair requires interpreting a concrete protocol value as a message,
    procedure, state, cause, operation, or another factual protocol concept, use
    established protocol-domain knowledge and do not guess when uncertain.

    ====================
    REPAIR SCOPE
    ====================

    Structured diagnosis issues define the repair scope.

    Repair only issues marked as repairable.

    Every issue marked as repairable must be materially addressed in the
    repaired executable logic.

    If the diagnosis identifies a specific executable construct as the cause
    of a repairable issue, that construct must not be returned unchanged.

    Merely reformatting XML, changing indentation, renaming descriptions,
    changing comments, or returning semantically equivalent defective logic
    does not constitute a repair.

    Preserve unaffected executable logic, but modify the executable logic
    responsible for each diagnosed repairable issue.

    Do not introduce unrelated changes merely because another formulation seems
    preferable.

    Semantic recommendations are supplementary guidance.

    They must not override:

    - the canonical monitoring task;
    - deterministic validation evidence;
    - supplied MMT protocol attribute knowledge;
    - the structured diagnosis.

    If the diagnosis indicates that repair is blocked because required
    information is unavailable, do not bypass that restriction by inventing the
    missing information.

    ====================
    DETERMINISTIC REPAIR REQUIREMENTS
    ====================

    Deterministic validation feedback is authoritative for the syntax or
    structural characteristic it checks.

    Every diagnosed deterministic error that is within the repair scope must be
    eliminated from the repaired candidate.

    Do not return unchanged a construct that the deterministic diagnosis
    explicitly identifies as invalid.

    When the diagnosis supplies supported or allowed values, use only those
    values if the corresponding construct is retained.

    For INVALID_OPERATOR_VALUE:

    - do not preserve the unsupported operator value;
    - do not substitute another undocumented operator value;
    - use only operator values documented in the supplied MMT property format;
    - if the invalid operator was attempting to express logical conjunction or
    disjunction, express that logic inside `boolean_expression` instead.

    For INVALID_PROPERTY_ARITY:

    - an MMT <property> element may contain at most two direct child elements;
    - the total number of direct <event> and/or <operator> children inside the
    <property> must not exceed two;
    - do not preserve a third direct child;
    - do not repair the error by merely adding, moving, or duplicating another
    direct <event> or <operator>;
    - reduce the property to a structurally supported representation using only
    mechanisms explicitly documented in the supplied MMT property format.

    More generally:

    - never return a repaired <property> containing more than two direct child
      elements;
    - do not invent unsupported XML operators;
    - do not invent undocumented nesting;
    - do not invent unsupported aggregation mechanisms, counters, stateful
      constructs, embedded-function syntax, or other MMT constructs merely to
      bypass the two-child limit;
    - a documented embedded function may be introduced when the canonical
      monitoring requirement genuinely requires additional computation or
      state, but not merely as a structural workaround for the arity error;
    - if the requested behavior requires MMT-specific functionality whose
      representation cannot be established from the supplied knowledge, do not
      fabricate that functionality.

    Preserve unrelated valid logic.

    ====================
    SEMANTIC REPAIR REQUIREMENTS
    ====================

    When repairing a semantic issue, modify executable monitoring logic rather
    than only changing human-readable descriptions.

    Relevant executable elements include:

    - boolean_expression;
    - event relationships;
    - operator structure;
    - temporal constraints;
    - event correlation;
    - threshold logic;
    - embedded-function logic when applicable.

    Do not treat a description or event label as sufficient evidence that the
    property implements the requested behavior.

    Preserve explicit numerical thresholds, timing requirements, event order,
    and task-defined correlations unless the diagnosis specifically identifies
    them as incorrect.

    If a semantic issue concerns a factual protocol-value mapping, use
    established protocol-domain knowledge.

    Do not invent another protocol value merely to make the property appear
    consistent.

    Do not treat the mere existence of a count-like attribute as proof that it
    implements a task-required threshold over correlated events.

    If the diagnosed semantic issue requires computation or state that cannot
    be adequately represented using ordinary documented MMT constructs, you may
    introduce or repair an embedded function using the documented MMT
    embedded-function mechanism.

    You may synthesize task-specific C algorithms required by the canonical
    monitoring task, including counters, temporal state, correlation state, or
    other ordinary C logic.

    When an embedded function receives protocol attributes as parameters:

    - protocol attribute knowledge may provide `security_c_type`;
    - when `security_c_type` is known, use that C type for the corresponding
      embedded-function parameter;
    - do not replace a known `security_c_type` with a generic pointer type or
      another inferred type;
    - if `security_c_type` is null, do not guess the embedded-function
      parameter type;
    - a null `security_c_type` means only that the embedded-function C
      representation is not established by the supplied knowledge; it does not
      mean that the protocol attribute itself is unavailable.    

    The generated algorithm must preserve all relevant explicit task semantics.

    Do not invent MMT APIs, helper functions, runtime facilities, libraries,
    lifecycle behavior, protocol attributes, or property-language features.

        When a PROPERTY_LOGIC_ERROR explicitly identifies an existing embedded
    function as defective, inspect and repair the actual C function body.

    In particular, if the diagnosis states that the embedded function:

    - lacks persistent state;
    - lacks a required counter or state update;
    - fails to separate state by a task-defined key;
    - omits an explicit threshold comparison;
    - returns a constant value instead of computing the required condition;
    - or contains placeholder logic;

    the repaired candidate must replace that defective logic with executable
    task-specific C implementing the corresponding canonical requirement.

    Do not return placeholder embedded-function implementations.

    Do not preserve an unconditional constant return when the canonical task
    requires a computed stateful condition.

    For example, an attribute such as packet_count must not be assumed to mean
    "number of task-matching events within the current property time window"
    unless that behavior is supported by the supplied MMT knowledge or other
    authoritative evidence.

    ====================
    AUTHORIZED TASK ASSUMPTIONS
    ====================

    Authorized assumptions are part of the operative monitoring specification.

    Preserve them during repair.

    Do not replace an authorized assumption with a different assumption.

    An authorized assumption may define an operational monitoring choice.

    It does not automatically establish unrelated factual protocol semantics.

    ====================
    UNRESOLVED TASK AMBIGUITIES
    ====================

    Every ambiguity still present in the canonical task remains unresolved.

    Do not resolve an unresolved ambiguity during repair by inventing:

    - a threshold;
    - a duration;
    - a protocol value;
    - an attribute mapping;
    - a source representation;
    - a correlation key;
    - another missing monitoring condition.

    Repair only what can be supported by the canonical task, authorized
    assumptions, supplied attribute knowledge, diagnosis, and established
    protocol-domain knowledge.

    ====================
    PROPERTY REPAIR SKILL
    ====================

    {context.repair_skill}

    ====================
    MMT PROPERTY FORMAT
    ====================

    {context.property_format}

    ====================
    PROPERTY RESTRICTIONS
    ====================

    {context.restrictions}

    ====================
    KNOWN GENERATION ERRORS
    ====================

    {context.common_errors}
    """.strip()

        user_content = f"""
    Repair the following MMT monitoring property.

    ====================
    CURRENT CANONICAL MONITORING TASK
    ====================

    {json.dumps(operative_task_data, indent=2)}

    The task above is the operative specification.

    Its requirements, restrictions, authorized assumptions, and unresolved
    ambiguities take precedence over historical or descriptive wording.

    If the canonical task explicitly defines a threshold, duration, identifier,
    correlation representation, or other operational mapping, preserve it unless
    the diagnosis explicitly identifies it as incorrect.

    ====================
    CURRENT PROPERTY
    ====================

    {current_property.xml}

    ====================
    CURRENT PROPERTY METADATA
    ====================

    {json.dumps(
        current_property.model_dump(
            mode="json"
        ),
        indent=2,
    )}

    ====================
    STRUCTURED REPAIR DIAGNOSIS
    ====================

    {json.dumps(
        diagnosis.model_dump(
            mode="json"
        ),
        indent=2,
    )}

    ====================
    SEMANTIC REPORT
    ====================

    {json.dumps(
        semantic_data,
        indent=2,
    )}

    ====================
    AVAILABLE MMT PROTOCOL ATTRIBUTE KNOWLEDGE
    ====================

    {json.dumps(model_protocol_attributes, indent=2)}

    ====================
    PROTOCOLS WITHOUT ATTRIBUTE KNOWLEDGE
    ====================

    {json.dumps(
        context.missing_attribute_knowledge,
        indent=2,
    )}

    Repair only the issues identified by the structured diagnosis.

    Every issue marked `repairable: true` must be materially addressed.

    Do not return unchanged the executable construct identified as the cause
    of a repairable semantic issue.

    If the diagnosis identifies an embedded-function implementation as the
    PROPERTY_LOGIC_ERROR, repair the actual C function body rather than merely
    reformatting or reproducing it.

    Preserve all unaffected executable logic.

    Do not introduce protocol attributes absent from the supplied MMT attribute
    knowledge.

    For factual protocol semantics, use the canonical task, authorized
    assumptions, and established protocol-domain knowledge available to you.

    Do not invent a semantic mapping when you cannot establish it with
    sufficient confidence.

    Task-defined operational mappings are authoritative and must not be replaced
    by alternative mappings merely because another representation appears
    plausible.

    Any construct explicitly identified as invalid by deterministic validation
    must not be returned unchanged.

    A repaired <property> must never contain more than two direct child
    elements.

    If INVALID_PROPERTY_ARITY is present in the structured diagnosis, the
    repaired property must contain at most two direct <event> and/or <operator>
    children.

    Do not bypass this constraint by inventing unsupported operators, nesting,
    aggregation mechanisms, counters, embedded-function syntax, or other
    undocumented MMT constructs.

    A documented embedded function may be introduced when the diagnosed
    semantic problem genuinely requires additional computation or state.
    It must not be introduced merely to hide a structural arity error.

    The repaired property must keep exactly this property identifier:

    {task.property_id}

    Return only the complete repaired XML document beginning with <beginning>
    and ending with </beginning>.

    Do not include Markdown code fences.
    Do not include explanations outside the XML.
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

    def repair(
        self,
        task: MonitoringTask,
        current_property: GeneratedProperty,
        diagnosis: RepairDiagnosis,
        semantic_report: (
            SemanticReport | None
        ) = None,
    ) -> RepairResult:
        """
        Perform at most one repair attempt.
        """

        if (
            diagnosis.status
            == RepairDiagnosisStatus.NO_REPAIR_NEEDED
        ):
            return RepairResult(
                task_id=task.id,
                status=(
                    RepairOutcomeStatus.NOT_NEEDED
                ),
                diagnosis=diagnosis,
                repaired_property=None,
                metadata={
                    "current_attempt":
                        current_property.attempt,
                },
            )

        if (
            diagnosis.status
            == RepairDiagnosisStatus.BLOCKED
        ):
            return RepairResult(
                task_id=task.id,
                status=(
                    RepairOutcomeStatus.BLOCKED
                ),
                diagnosis=diagnosis,
                repaired_property=None,
                metadata={
                    "current_attempt":
                        current_property.attempt,
                    "blocking_reasons":
                        diagnosis.blocking_reasons,
                },
            )

        context = self.context_builder.build(
            task
        )

        messages = self._build_messages(
            task=task,
            current_property=current_property,
            diagnosis=diagnosis,
            context=context,
            semantic_report=semantic_report,
        )

        response = self.client.complete(
            messages
        )

        try:
            xml = extract_mmt_xml(
                response.content
            )

        except PropertyGenerationError as exc:
            raise PropertyRepairError(
                "The repair model did not return a "
                "complete MMT XML document."
            ) from exc

        _check_repaired_property_id(
            xml=xml,
            expected_property_id=(
                task.property_id
            ),
        )

        repair_issue_codes = [
            issue.code
            for issue in diagnosis.issues
            if issue.repairable
        ]

        repaired_property = GeneratedProperty(
            task_id=task.id,
            xml=xml,
            model=self.client.config.model,
            attempt=(
                current_property.attempt + 1
            ),
            metadata={
                "property_id":
                    task.property_id,
                "protocols":
                    task.protocols,
                "repair_of_attempt":
                    current_property.attempt,
                "repair_issue_codes":
                    repair_issue_codes,
                "provider_model":
                    response.model,
                "usage":
                    response.usage,
            },
        )

        return RepairResult(
            task_id=task.id,
            status=RepairOutcomeStatus.REPAIRED,
            diagnosis=diagnosis,
            repaired_property=repaired_property,
            metadata={
                "repair_of_attempt":
                    current_property.attempt,
            },
        )