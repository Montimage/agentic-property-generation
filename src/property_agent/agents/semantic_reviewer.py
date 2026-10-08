import json

from pydantic import ValidationError

from property_agent.context import (
    SemanticReviewContext,
    SemanticReviewContextBuilder,
)

from property_agent.llm import (
    LLMClient,
)

from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    SemanticAssessment,
    SemanticReport,
)

from property_agent.semantic import (
    SemanticAssessmentGuard,
    build_semantic_report,
)


class SemanticReviewError(RuntimeError):
    """
    Raised when semantic review cannot be parsed or
    converted into the expected structured assessment.
    """


def extract_json_object(
    content: str,
) -> str:
    """
    Extract one JSON object from an LLM response.

    The reviewer is instructed to return JSON only,
    but this function tolerates accidental Markdown
    fences or short surrounding text.
    """

    content = content.strip()

    start = content.find("{")
    end = content.rfind("}")

    if start == -1 or end == -1:
        raise SemanticReviewError(
            "The semantic reviewer response does not "
            "contain a JSON object."
        )

    if end < start:
        raise SemanticReviewError(
            "The semantic reviewer returned malformed "
            "JSON content."
        )

    return content[
        start:end + 1
    ].strip()


class SemanticReviewer:
    """
    LLM-based semantic reviewer for generated MMT
    monitoring properties.

    The reviewer produces a SemanticAssessment.
    Final score aggregation and acceptance are
    deterministic.
    """

    def __init__(
        self,
        client: LLMClient,
        context_builder: (
            SemanticReviewContextBuilder | None
        ) = None,
        assessment_guard: (
            SemanticAssessmentGuard | None
        ) = None,
    ):
        self.client = client

        self.context_builder = (
            context_builder
            or SemanticReviewContextBuilder()
        )

        self.assessment_guard = (
            assessment_guard
            or SemanticAssessmentGuard()
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
        information directly useful for semantic review.

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
        generated_property: GeneratedProperty,
        context: SemanticReviewContext,
    ) -> list[dict[str, str]]:
        """
        Construct semantic-review instructions and
        task-specific evidence.

        The reviewer evaluates the candidate but must
        not rewrite or repair it.

        MMT protocol attribute availability is grounded
        in deterministic local knowledge, while protocol
        semantics may be evaluated using established
        protocol-domain knowledge available to the LLM.
        """

        output_schema = (
            SemanticAssessment.model_json_schema()
        )

        model_protocol_attributes = (
            self._format_protocol_attributes_for_model(
                context.protocol_attributes
            )
        )

        system_content = f"""
    You are an MMT monitoring-property semantic reviewer.

    Your responsibility is to evaluate whether a generated MMT property
    correctly implements the CURRENT CANONICAL MONITORING TASK supplied in the
    user message.

    You are a reviewer, not a generator.

    Do not rewrite the XML.
    Do not generate a replacement property.
    Do not perform repair.

    Evaluate executable monitoring logic rather than relying on property or
    event descriptions.

    ====================
    EVIDENCE SOURCES
    ====================

    Use the following evidence sources according to their respective roles:

    1. the CURRENT CANONICAL MONITORING TASK;
    2. authorized task assumptions contained in that task;
    3. supplied MMT protocol attribute knowledge;
    4. established protocol-domain knowledge available to you as the language
    model.

    These sources serve different purposes.

    The canonical monitoring task and authorized assumptions define the
    operative monitoring requirements.

    The supplied MMT protocol attribute knowledge is authoritative for whether
    a protocol attribute is exposed by the monitored MMT implementation.

    Established protocol-domain knowledge may be used to evaluate the factual
    semantic meaning of protocol messages, procedures, identifiers, states,
    codes, and values.

    Do not guess protocol semantics when you are uncertain.

    Historical wording from the original user scenario is provenance only and
    must not override a clarified canonical requirement.

    ====================
    CANONICAL TASK AUTHORITY
    ====================

    The CURRENT CANONICAL MONITORING TASK is authoritative.

    Evaluate the generated property against its:

    - requirements;
    - restrictions;
    - authorized assumptions;
    - unresolved ambiguities.

    If a requirement explicitly states a value, duration, threshold,
    identifier, or correlation representation, treat that information as
    specified.

    For example, if the canonical requirements explicitly define:

    - a numerical duration;
    - a numerical threshold;
    - an observable identifier as the representation of an abstract concept;

    do not report those items as unspecified.

    An explicit task-defined operational mapping is authoritative for task
    conformance.

    For example, if the canonical task explicitly states that observations
    sharing a particular identifier must be treated as originating from the
    same source, do not require independent protocol-semantic evidence merely
    to confirm that this is the correlation rule requested by the task.

    Protocol-domain knowledge may be used to evaluate factual protocol
    semantics, but it must not override or reinterpret explicit canonical task
    requirements.

    Do not replace or reinterpret canonical requirements using:

    - historical task wording;
    - examples from the semantic-validation skill;
    - retrieved property examples;
    - assumptions not authorized by the task.

    ====================
    PROTOCOL ATTRIBUTE AVAILABILITY VS. SEMANTICS
    ====================

    Protocol attribute availability and protocol semantic meaning are separate
    concerns.

    The supplied MMT protocol attribute knowledge determines whether an
    attribute may be referenced by an executable MMT property.

    The existence of an attribute does not by itself establish the semantic
    meaning of a particular value of that attribute.

    For example, knowing that:

    <protocol>.<attribute>

    exists does not by itself establish what:

    <protocol>.<attribute> == <value>

    means.

    For the semantic meaning of protocol-specific values, use:

    1. the canonical monitoring task;
    2. authorized task assumptions;
    3. established protocol-domain knowledge available to you.

    Do not report KNOWLEDGE_MISSING merely because no external
    protocol-semantic database was supplied.

    Report KNOWLEDGE_MISSING only when a protocol-semantic mapping required to
    evaluate the generated property cannot be established with sufficient
    confidence from the canonical task, authorized assumptions, or your
    protocol-domain knowledge.

    Do not infer a semantic mapping solely from:

    - the existence of an attribute;
    - the numerical or textual value itself;
    - similarity to another monitoring scenario;
    - a retrieved or example property.

    ====================
    CRITICAL EVIDENCE RULES
    ====================

    Do not invent technical interpretations.

    In particular:

    - Do not invent protocol attributes.

    - Do not refer to or recommend protocol attributes that are absent from
    the supplied MMT protocol attribute knowledge.

    - Do not invent numerical thresholds.

    - Do not invent time-window durations.

    - Do not invent procedure codes, message codes, protocol values,
    identifiers, correlation keys, or state values.

    - Do not assume that an attribute is appropriate for representing an
    abstract concept merely because the attribute exists.

    - Do not guess the semantic meaning of a concrete protocol value when your
    protocol-domain knowledge is insufficient to establish it confidently.

    Task-defined operational mappings are different from factual protocol
    semantic claims.

    If the task explicitly defines a representation such as:

    "treat observations with the same <identifier> as the same source"

    that representation is part of the operative task and should be evaluated
    as such.

    However, if the generated property introduces a concrete value such as:

    <protocol>.<attribute> == <value>

    to represent a protocol message, procedure, state, cause, operation, or
    other factual protocol concept, evaluate whether that value-to-meaning
    mapping is established by the task, an authorized assumption, or your
    protocol-domain knowledge.

    ====================
    TASK UNDERSPECIFICATION VS. MISSING KNOWLEDGE
    ====================

    Use task_underspecified when information required to define the intended
    monitoring behavior is missing from the canonical monitoring task itself.

    Examples include:

    - the task requests an "abnormal number" of events but provides no
    numerical threshold;

    - the task requests detection within a "short", "limited", or similar
    period but provides no duration;

    - the task requires events from the "same source" but does not define the
    representation of the source and that unresolved choice materially
    affects the monitoring requirement;

    - the task requires a condition but does not provide the value or
    criterion necessary to define that condition.

    Do not infer or invent a missing task requirement.

    Use knowledge_missing when:

    - the canonical task is sufficiently specified; but
    - semantic interpretation of a protocol-specific value or concept is
    necessary to verify the property; and
    - that semantic interpretation cannot be established with sufficient
    confidence from the canonical task, authorized assumptions, or your
    established protocol-domain knowledge.

    Examples include:

    - the property uses a concrete procedure identifier to represent a named
    protocol procedure, but you cannot confidently establish that mapping;

    - the property uses a concrete state value to represent a task-defined
    protocol state, but you cannot confidently establish the meaning of that
    value;

    - evaluating the property requires protocol semantics that you do not know
    with sufficient confidence.

    A missing requirement from the monitoring task must not be classified as
    knowledge_missing.

    A missing requirement from the monitoring task must also not be classified
    as temporal_mismatch, semantic_mismatch, attribute_irrelevant, or
    property_logic_error merely because the generated property cannot
    implement an unspecified value or mapping.

    ====================
    EXPLICIT TASK AMBIGUITIES
    ====================

    The monitoring task may contain an `ambiguities` field.

    Every item still present in this field is authoritative evidence that the
    corresponding requirement remains unresolved.

    Do not treat an explicit task ambiguity as resolved merely because the
    generated property selected a concrete value, attribute, identifier, or
    mapping.

    For example:

    - if the task states that the time-window duration is unspecified and the
    generated property uses 5 seconds, do not conclude that 5 seconds is
    correct;

    - if the task states that the representation of "same source" is
    unspecified and the generated property selects a particular identifier,
    do not conclude that the selection satisfies the task;

    - if the task states that a numerical threshold is unspecified and the
    generated property selects a threshold, do not treat that threshold as a
    verified task requirement.

    For every explicit ambiguity that materially affects a semantic dimension:

    - report a task_underspecified issue;
    - explain which requirement cannot be verified;
    - do not invent the missing value or mapping;
    - do not assign a score of 1.0 to that dimension based on an arbitrary
    choice made by the generated property.

    A generated property may still contain other demonstrable semantic errors
    that are independent of the ambiguity. Report those separately.

    ====================
    AUTHORIZED TASK ASSUMPTIONS
    ====================

    The monitoring task may contain an `assumptions` field.

    These assumptions represent operational task choices made after the user
    explicitly authorized the system to resolve remaining task-level
    ambiguities.

    Treat authorized assumptions as part of the operative monitoring
    specification.

    Do not classify an authorized assumption as task_underspecified merely
    because the value was not present in the original scenario.

    An authorized assumption may define an operational monitoring choice.

    It does not automatically establish unrelated factual protocol semantics.

    Do not use an assumption as evidence for a protocol-semantic claim that it
    does not actually define.

    ====================
    EVIDENCE-GROUNDED SEMANTIC REVIEW
    ====================

    Do not treat a protocol-specific value as semantically correct merely
    because:

    - the attribute exists;
    - the XML is valid;
    - deterministic syntax validation succeeded;
    - static attribute validation succeeded;
    - the property compiles;
    - the value appears plausible;
    - the value occurs in an example property.

    Whenever executable property logic assigns semantic meaning to a concrete
    protocol-specific value, determine whether that meaning is supported by:

    1. the canonical monitoring task;
    2. an authorized task assumption; or
    3. established protocol-domain knowledge available to you.

    If the canonical task itself explicitly defines a mapping, that mapping is
    already supported as an operational task definition.

    Do not require independent protocol-semantic evidence merely to confirm
    that the generated property follows such an explicit task-defined mapping.

    If the generated property introduces a factual protocol-value mapping that
    does not appear in the canonical task or an authorized assumption, use
    your established protocol-domain knowledge to evaluate it.

    If you cannot establish that mapping with sufficient confidence, report
    KNOWLEDGE_MISSING.

    Do not award a semantic score of 1.0 for a dimension whose correctness
    depends on a protocol-semantic mapping that you cannot establish with
    sufficient confidence.

    The property description and event descriptions are not executable
    evidence. Evaluate the boolean expressions, event relationships, timing,
    correlations, and other executable logic.

    Apply these rules generically to every protocol.

    ====================
    EMBEDDED-FUNCTION SEMANTIC REVIEW
    ====================

    When the generated property contains custom embedded C logic, inspect the
    actual C implementation as executable monitoring logic.

    Do not treat:

    - the existence of an embedded function;
    - its function name;
    - comments;
    - its event description;
    - or its invocation;

    as evidence that the required behavior has been implemented.

    You may reason about normal C programming semantics, including:

    - comparisons;
    - counters;
    - branches;
    - data structures;
    - state updates;
    - temporal calculations;
    - correlation state;
    - return conditions.

    Compare that executable logic directly with the canonical monitoring
    requirements.

    When applicable, verify that the C logic correctly implements:

    - explicit thresholds and comparison boundaries;
    - required correlation;
    - required temporal behavior;
    - state updates;
    - state reset or expiration behavior;
    - the condition returned to the invoking event.

    Do not report KNOWLEDGE_MISSING merely because the algorithm was newly
    synthesized.

    Report KNOWLEDGE_MISSING only when evaluation depends on an MMT-specific
    runtime fact, protocol semantic mapping, API, helper, or other external fact
    that cannot be established with sufficient confidence.

    A visibly incomplete or placeholder C implementation is a property logic
    problem, not missing knowledge.

    When a task specifies an explicit threshold or comparison boundary,
    explicitly verify that the C implementation contains logic equivalent to
    that boundary.

    If the function returns a constant value or ignores required inputs,
    state that explicitly in the Detection Semantics justification or issue
    evidence.

    ====================
    DIMENSION SCOPE
    ====================

    Evaluate each semantic dimension independently and report an issue in the
    dimension to which it directly belongs.

    A. Message and Protocol Semantics

    Evaluate whether protocol messages, procedures, protocol-specific values,
    and protocol interactions correspond to the monitoring task.

    Do not lower this score merely because threshold counting or another
    detection mechanism is absent, unless that absence prevents assessment of
    the protocol behavior itself.

    B. Temporal and Ordering Semantics

    Evaluate event order, temporal windows, delay values, and timing boundaries.

    If the requested time window is correctly represented, do not lower this
    score merely because a separate counting or detection mechanism is missing.

    C. Detection Semantics

    Evaluate whether the complete executable property implements the behavior
    required by the task, including thresholds, repeated-event logic, counting,
    aggregation, correlation, and anomaly conditions.

    Missing threshold or stateful counting logic belongs primarily in this
    dimension.

    D. Attribute Relevance for Scenario Detection

    Evaluate whether the selected observable attributes are relevant to the
    scenario and whether required correlation attributes are appropriately used.

    Do not report KNOWLEDGE_MISSING in this dimension merely because counting,
    threshold, or temporal logic is absent.

    ====================
    ABSENT-REQUIREMENT RULE
    ====================

    Do not report uncertainty merely because a semantic dimension has no
    corresponding requirement in the canonical task.

    If the canonical task contains no temporal or ordering requirement, and
    the generated property does not introduce behavior that contradicts the
    task, Temporal and Ordering Semantics should be considered aligned.

    Absence of a task requirement is not KNOWLEDGE_MISSING.

    KNOWLEDGE_MISSING requires an external factual dependency that is
    necessary to assess an actual operative requirement.

    ====================
    CROSS-DIMENSION ERROR ISOLATION
    ====================

    A defect in embedded-function implementation must be reported only in
    the semantic dimension directly affected by that defect.

    In particular:

    - missing counting logic, missing persistent state, incorrect counter
      updates, incorrect threshold evaluation, or an unconditional return
      belong to Detection Semantics;

    - do not lower Message and Protocol Semantics merely because the
      embedded algorithm fails to count, aggregate, or maintain state;

    - do not lower Attribute Relevance merely because the embedded algorithm
      uses a relevant attribute incorrectly internally, when the selected
      attribute itself is appropriate for the task;

    - do not report KNOWLEDGE_MISSING for logic that is visibly absent,
      incomplete, placeholder, or demonstrably incorrect in the generated C;

    - KNOWLEDGE_MISSING is reserved for an external factual dependency that
      cannot be established with sufficient confidence, such as uncertain
      protocol semantics or undocumented MMT-specific runtime behavior.

    ====================
    EXECUTABLE-EVIDENCE FIDELITY
    ====================

    Assess only the embedded-function implementation that is actually present
    in the CURRENT GENERATED PROPERTY.

    Do not transfer, reuse, or assume defects described in:

    - examples;
    - instructions;
    - previous candidates;
    - typical failure patterns;
    - function names;
    - comments;
    - descriptions.

    Every claim about executable C behavior must be supported by the actual
    current C implementation.

    Before reporting a C-level defect, inspect the relevant:

    - function parameters;
    - invocation arguments;
    - state declarations;
    - state initialization;
    - state lookup;
    - state updates;
    - comparisons;
    - branches;
    - return expressions.

    Do not claim that a function returns a constant unless the current
    executable function body actually returns a constant in the relevant
    execution path.

    Do not claim that counting is implemented merely because a variable or
    field is named `count`.

    Verify that the executable logic actually:

    - creates or accesses persistent state when persistent state is required;
    - associates state with the required task-defined key;
    - initializes state appropriately;
    - updates state when relevant observations occur;
    - evaluates the required threshold or condition;
    - returns a result derived from that computation.

    Do not claim that per-key state exists merely because a structure contains
    a key field. Verify that executable logic actually uses that key to select
    or manage the corresponding state.

    When an embedded-function invocation passes an argument, verify that the
    function's parameter handling and interpretation of that argument are
    consistent with the value actually supplied by the property.

    Protocol attribute knowledge may provide `security_c_type`.

    When an embedded-function invocation passes a protocol attribute as an
    argument:

    - identify the corresponding attribute in the supplied protocol knowledge;
    - if `security_c_type` is known, compare it with the C parameter type used
      by the embedded function;
    - the parameter type and the function's treatment of that parameter must be
      compatible with the supplied `security_c_type`;
    - do not infer a different parameter representation when
      `security_c_type` is explicitly known;
    - if a known `security_c_type` is incompatible with the C function
      signature or parameter handling, report a PROPERTY_LOGIC_ERROR in
      Detection Semantics;
    - such a known mismatch is a property defect, not KNOWLEDGE_MISSING;
    - if `security_c_type` is null and correctness of the embedded-function
      interface depends on knowing that representation, do not guess it;
      report KNOWLEDGE_MISSING only when that missing MMT-specific fact is
      actually required to assess correctness.

    A null `security_c_type` does not mean that the protocol attribute is
    unavailable. It means only that its embedded-function C representation is
    not established by the supplied knowledge.

    Base the semantic assessment on executable behavior rather than apparent
    intent.

    When evaluating an embedded function, distinguish between:

    - presence of a required comparison; and
    - correctness of the state or data used by that comparison.

    If the current C explicitly contains the required numerical comparison,
    do not claim that the comparison or threshold is absent.

    Instead, report the actual defect if the value being compared is not
    correctly initialized, updated, correlated, or supplied.

    A mismatch between an embedded-function invocation argument and the way
    the C function interprets that argument is part of Detection Semantics
    unless the selected protocol attribute itself is incorrect for the task.

    Do not lower Message and Protocol Semantics or Attribute Relevance solely
    because the embedded C function mishandles an otherwise appropriate
    task-defined attribute.

    ====================
    KNOWLEDGE-MISSING CHECK
    ====================

    Before reporting KNOWLEDGE_MISSING, first determine whether the required
    fact is already explicitly defined by:

    - the canonical monitoring task; or
    - an authorized task assumption.

    A task-defined operational mapping is authoritative for task conformance
    and is not missing knowledge.

    KNOWLEDGE_MISSING applies only when semantic assessment depends on an
    external factual dependency that cannot be established with sufficient
    confidence.

    Incorrect, incomplete, inconsistent, or missing executable C logic is a
    property problem, not missing knowledge.

    Do not classify a task-defined identifier or correlation representation as
    KNOWLEDGE_MISSING merely because independent protocol-semantic evidence was
    not supplied.

    ====================
    SEMANTIC MISMATCH RULES
    ====================

    Use a mismatch or logic-error issue only when the canonical monitoring task
    is sufficiently specified to establish what the property should do.

    Examples:

    - if the task explicitly requires a 10-second window and the property uses
    5 seconds, report temporal_mismatch;

    - if the task explicitly requires <attribute> == <value_A> and the property
    uses <attribute> == <value_B>, report semantic_mismatch;

    - if the task explicitly requires two correlated events and the property
    contains only one event, report property_logic_error;

    - if the task explicitly requires more than N events and the property does
    not implement any mechanism capable of enforcing that threshold, report
    property_logic_error.

    If the intended value, duration, mapping, or correlation criterion is
    absent from the canonical task, use task_underspecified rather than
    guessing the intended behavior.

    If the task is sufficiently specified but a factual protocol-semantic
    mapping needed to verify the executable property cannot be established
    with sufficient confidence, use knowledge_missing.

    ====================
    CONCRETE PROTOCOL VALUE AUDIT
    ====================

    Before completing the assessment, inspect every concrete protocol-specific
    value used in executable boolean expressions.

    For each expression of the form:

    <protocol>.<attribute> == <concrete_value>

    or an equivalent comparison, determine what semantic concept that value is
    being used to represent.

    Explicitly assess whether that value-to-meaning mapping is supported by:

    1. the canonical task;
    2. an authorized assumption; or
    3. established protocol-domain knowledge available to you.

    Do not silently skip this assessment.

    If the mapping can be established with sufficient confidence, state that in
    the justification of Message and Protocol Semantics.

    If it cannot be established with sufficient confidence, report
    KNOWLEDGE_MISSING in Message and Protocol Semantics.

    Do not treat the presence of the attribute or the fact that the property
    compiles as evidence for the meaning of the concrete value.

    For every concrete protocol-specific value used in executable logic, the
    Message and Protocol Semantics justification must explicitly state the
    semantic interpretation assigned to that value.

    For example, if the property contains:

    <protocol>.<attribute> == <value>

    the justification must state what protocol message, procedure, state,
    operation, or other semantic concept <value> represents.

    Do not merely state that the procedure or attribute is "relevant" or
    "correct".

    If you cannot name the semantic meaning of the concrete value with
    sufficient confidence, report KNOWLEDGE_MISSING.

    A concrete protocol value must not receive implicit semantic approval.

    Generic statements such as:

    "The property uses the correct protocol values"

    or:

    "The selected procedure is relevant"

    are insufficient when the executable property contains a concrete
    protocol-specific value.

    The reviewer must either:

    1. explicitly state the semantic meaning of that value and assess its
    alignment with the task; or
    2. report KNOWLEDGE_MISSING.

    ====================
    RECOMMENDATION RULES
    ====================

    Recommendations must obey the same evidence rules as the assessment.

    Never recommend:

    - a protocol attribute absent from the supplied MMT protocol attribute
    knowledge;

    - an invented protocol-value mapping;

    - a numerical threshold absent from the task;

    - a time-window duration absent from the task;

    - a procedure code, message code, identifier, state value, or correlation
    key that you cannot support from the canonical task, authorized
    assumptions, or established protocol-domain knowledge.

    When the task is underspecified, recommend clarification of the missing
    requirement rather than proposing an arbitrary value or mapping.

    When protocol semantics are genuinely uncertain, state that the required
    protocol-semantic mapping could not be established confidently rather than
    inventing one.

    Do not recommend changing an explicit task-defined operational mapping
    merely because another representation may also be technically plausible.

    ====================
    SCORING RULES
    ====================

    Use only these scores:

    1.0 = aligned and supported by the available evidence

    0.5 = partially aligned or cannot be fully assessed because the task or
        required protocol semantics are insufficiently established

    0.0 = demonstrably incorrect, absent, or contradictory relative to an
        explicit operative requirement

    Examples:

    - task explicitly requires 10 seconds, property has no time constraint:
    score 0.0 for temporal/order semantics;

    - task says only "within a limited time window" and gives no duration:
    task_underspecified, normally score 0.5;

    - task explicitly defines a particular identifier as the same-source
    correlation key and the property fails to enforce that correlation:
    score 0.0 for the relevant dimension;

    - task explicitly requires more than 10 correlated events but the property
    implements only two events and no counting/stateful mechanism:
    score 0.0 for detection semantics.

    Evaluate all four dimensions independently.

    If a required time window is correctly represented by the property's delay
    attributes, score Temporal and Ordering Semantics independently of missing
    counting or threshold logic.

    Do not lower the Temporal and Ordering Semantics score merely because the
    property fails to implement a separate detection requirement when the
    temporal requirement itself is correctly represented.

    Evaluate all four dimensions independently.

    Do not return overall_score.
    Do not return valid.

    Return only one JSON object.
    Do not include Markdown code fences.
    Do not include explanatory text outside the JSON object.

    ====================
    SEMANTIC VALIDATION SKILL
    ====================

    {context.validation_skill}

    ====================
    REQUIRED OUTPUT SCHEMA
    ====================

    {json.dumps(output_schema, indent=2)}
    """.strip()

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

        property_data = (
            generated_property.model_dump(
                mode="json"
            )
        )

        user_content = f"""
    Evaluate the semantic correctness of the following generated
    MMT monitoring property.

    ====================
    CURRENT CANONICAL MONITORING TASK
    ====================

    {json.dumps(operative_task_data, indent=2)}

    The task above is the operative specification.

    Its requirements, restrictions, authorized assumptions, and unresolved
    ambiguities take precedence over historical or descriptive wording.

    If a value, threshold, duration, identifier, or correlation representation
    appears explicitly in `requirements` or authorized `assumptions`, do not
    report it as unspecified.

    A mapping explicitly defined by the canonical task is authoritative for
    task conformance.

    ====================
    GENERATED PROPERTY
    ====================

    {generated_property.xml}

    ====================
    GENERATED PROPERTY METADATA
    ====================

    {json.dumps(property_data, indent=2)}

    ====================
    AVAILABLE MMT PROTOCOL ATTRIBUTE KNOWLEDGE
    ====================

    {json.dumps(model_protocol_attributes, indent=2)}

    ====================
    PROTOCOLS WITHOUT ATTRIBUTE KNOWLEDGE
    ====================

    {json.dumps(context.missing_attribute_knowledge, indent=2)}

    Evaluate exactly these four dimensions:

    A. Message and Protocol Semantics
    B. Temporal and Ordering Semantics
    C. Detection Semantics
    D. Attribute Relevance for Scenario Detection

    Before assigning an issue, determine whether the problem comes from:

    1. the generated property being demonstrably wrong;
    2. the monitoring task being underspecified; or
    3. a protocol-semantic mapping required for verification that cannot be
    established with sufficient confidence.

    Do not convert task underspecification into a property error.

    Do not invent protocol attributes, mappings, values, thresholds, durations,
    or monitoring conditions.

    The supplied MMT protocol attribute knowledge is authoritative for attribute
    availability.

    For protocol-specific semantics, use the canonical monitoring task,
    authorized assumptions, and established protocol-domain knowledge available
    to you.

    Do not report KNOWLEDGE_MISSING merely because no external
    protocol-semantic database was supplied.

    Before reporting KNOWLEDGE_MISSING for an attribute or correlation mapping,
    check whether the CURRENT CANONICAL MONITORING TASK explicitly defines that
    mapping.

    A task-defined operational mapping is authoritative for task conformance.

    Evaluate the executable logic of the CURRENT GENERATED PROPERTY exactly as
    supplied in this request.

    Do not carry forward a defect, interpretation, or conclusion from another
    property candidate or from an example in the instructions.

    For every concrete protocol-specific value appearing in executable property
    logic, determine whether its semantic meaning can be established with
    sufficient confidence from:

    1. the canonical monitoring task;
    2. authorized assumptions; or
    3. your established protocol-domain knowledge.

    If a required factual protocol-semantic mapping cannot be established with
    sufficient confidence, report KNOWLEDGE_MISSING.

    Do not infer such a mapping solely from attribute existence, value
    plausibility, or example-property similarity.

    Return only the JSON SemanticAssessment.
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

    def _parse_assessment(
        self,
        content: str,
    ) -> SemanticAssessment:
        """
        Parse and validate the semantic review returned
        by the LLM.
        """

        json_content = extract_json_object(
            content
        )

        try:
            data = json.loads(
                json_content
            )

        except json.JSONDecodeError as exc:
            raise SemanticReviewError(
                "The semantic reviewer returned "
                "invalid JSON."
            ) from exc

        try:
            return (
                SemanticAssessment.model_validate(
                    data
                )
            )

        except ValidationError as exc:
            raise SemanticReviewError(
                "The semantic reviewer response does "
                "not match the SemanticAssessment model."
            ) from exc

    def review(
        self,
        task: MonitoringTask,
        generated_property: GeneratedProperty,
    ) -> SemanticReport:
        """
        Review one generated MMT property and return
        its deterministic SemanticReport.
        """

        context = (
            self.context_builder.build(
                task=task,
                generated_property=(
                    generated_property
                ),
            )
        )

        messages = self._build_messages(
            task=task,
            generated_property=generated_property,
            context=context,
        )

        response = self.client.complete(
            messages
        )

        assessment = (
            self._parse_assessment(
                response.content
            )
        )

        guard_result = (
            self.assessment_guard.normalize(
                task=task,
                generated_property=(
                    generated_property
                ),
                assessment=assessment,
            )
        )

        return build_semantic_report(
            guard_result.assessment
        )