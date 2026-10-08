import json

from pydantic import ValidationError

from property_agent.context import (
    TaskInterpretationContext,
    TaskInterpretationContextBuilder,
)

from property_agent.llm import (
    LLMClient,
)

from property_agent.models import (
    MonitoringTask,
    NaturalLanguageScenario,
    TaskInterpretation,
    TaskInterpretationResult,
    TaskClarificationUpdate,
)


class TaskInterpretationError(
    RuntimeError
):
    """
    Raised when a natural-language monitoring scenario
    cannot be converted into the expected structured
    interpretation.
    """


def extract_interpretation_json(
    content: str,
) -> str:
    """
    Extract one JSON object from the LLM response.

    The model is instructed to return JSON only, but
    accidental Markdown fences or surrounding text are
    tolerated.
    """

    content = content.strip()

    start = content.find("{")
    end = content.rfind("}")

    if (
        start == -1
        or end == -1
        or end < start
    ):
        raise TaskInterpretationError(
            "The task interpreter response does not "
            "contain a valid JSON object."
        )

    return content[
        start:end + 1
    ].strip()

def _deduplicate(
    values: list[str],
) -> list[str]:
    """
    Preserve ordering while removing duplicates.
    """

    return list(
        dict.fromkeys(values)
    )

def _apply_text_updates(
    current: list[str],
    updates,
) -> tuple[
    list[str],
    list[dict[str, str | None]],
    list[dict[str, str | None]],
]:
    """
    Apply clarification updates deterministically.

    A replacement is accepted only when `previous`
    exactly matches an existing canonical item.

    This prevents the LLM from deleting or rewriting
    unrelated task information.
    """

    result = list(
        current
    )

    applied = []
    ignored = []

    for update in updates:

        # ----------------------------------------------
        # New information
        # ----------------------------------------------

        if update.previous is None:
            if update.value not in result:
                result.append(
                    update.value
                )

            applied.append(
                {
                    "previous": None,
                    "value": update.value,
                }
            )

            continue

        # ----------------------------------------------
        # Refinement / replacement
        # ----------------------------------------------

        if update.previous not in result:
            ignored.append(
                {
                    "previous":
                        update.previous,
                    "value":
                        update.value,
                }
            )

            continue

        index = result.index(
            update.previous
        )

        result[index] = (
            update.value
        )

        applied.append(
            {
                "previous":
                    update.previous,
                "value":
                    update.value,
            }
        )

    return (
        _deduplicate(result),
        applied,
        ignored,
    )

class TaskInterpreter:
    """
    LLM-backed natural-language monitoring-task
    interpreter.

    The interpreter extracts structured task semantics
    but does not generate or repair MMT properties.
    """

    def __init__(
        self,
        client: LLMClient,
        context_builder: (
            TaskInterpretationContextBuilder
            | None
        ) = None,
    ):
        self.client = client

        self.context_builder = (
            context_builder
            or TaskInterpretationContextBuilder()
        )

    def _build_messages(
        self,
        scenario: NaturalLanguageScenario,
        context: TaskInterpretationContext,
    ) -> list[dict[str, str]]:
        """
        Build extraction instructions for one
        natural-language scenario.
        """

        output_schema = (
            TaskInterpretation
            .model_json_schema()
        )

        system_content = f"""
    You are a monitoring-task interpretation agent.

    Your responsibility is to convert a natural-language monitoring
    scenario into a structured task interpretation.

    You are an interpreter, not a property generator.

    Do not generate XML.
    Do not generate an MMT property.
    Do not perform semantic validation.
    Do not repair the scenario.

    Extract only information supported by:

    1. the original natural-language scenario;
    2. explicit USER CLARIFICATIONS, when present.

    Do not invent:

    - numerical thresholds;
    - time-window durations;
    - protocol identifiers;
    - procedure codes;
    - message codes;
    - protocol attributes;
    - correlation keys;
    - monitoring conditions;
    - restrictions.

    ====================
    REQUIREMENT EXTRACTION
    ====================

    Preserve every explicit monitoring requirement stated by the user.

    Requirements may include:

    - event counts;
    - protocol values;
    - timing constraints;
    - ordering constraints;
    - correlation conditions;
    - monitoring conditions;
    - explicitly stated attributes or identifiers.

    Preserve explicit numerical values exactly as provided.

    Preserve qualifiers that affect the meaning of a requirement.

    Examples include:

    - exactly;
    - at least;
    - at most;
    - more than;
    - less than;
    - same;
    - different;
    - within;
    - before;
    - after.

    Do not convert an abstract concept into a more specific technical
    representation unless the user explicitly supplied that representation.

    For example:

    "same source"

    must not automatically become:

    "same connection identifier",
    "same endpoint identifier",
    "same entity identifier",
    "same session identifier",

    unless the user explicitly states the corresponding mapping.

    The interpreter must preserve the abstract concept as unresolved when a
    concrete representation is required but has not been provided.

    ====================
    RESTRICTION EXTRACTION
    ====================

    Explicit negative constraints and prohibitions are important task
    information and must not be discarded.

    Preserve every explicit limitation, prohibition, or construction
    constraint in the `restrictions` field.

    Statements using expressions such as:

    - "do not";
    - "must not";
    - "only";
    - "without";
    - "avoid";
    - "do not introduce";
    - "do not use";
    - "use only";

    must be preserved as restrictions when they constrain the monitoring
    logic or generated property.

    Examples:

    "Do not introduce additional procedure codes."

    must be preserved as a restriction.

    "Do not introduce additional procedure codes or correlation attributes."

    must be preserved as a restriction.

    "Use only procedure_code 4."

    contains both:

    - a positive monitoring constraint that may belong in requirements; and
    - a limitation that must also be preserved in restrictions when needed
    to retain the user's intent.

    Do not omit an explicit restriction merely because related information
    also appears in a requirement.

    Do not create restrictions that the user did not state.

    ====================
    RESTRICTION SCOPE AND QUALIFIERS
    ====================

    Preserve the semantic scope of modifiers and qualifiers when extracting
    restrictions.

    Words and expressions such as:

    - additional;
    - only;
    - same;
    - different;
    - exactly;
    - at least;
    - at most;
    - more than;
    - less than;

    must not be removed when doing so would change the user's intended
    constraint.

    When one modifier applies to multiple coordinated items, preserve that
    scope for every affected item.

    For example:

    "Do not introduce additional procedure codes or correlation attributes."

    may be preserved as one restriction:

    "Do not introduce additional procedure codes or correlation attributes."

    or, if split, it must preserve the modifier correctly:

    "Do not introduce additional procedure codes."
    "Do not introduce additional correlation attributes."

    It must not become:

    "Do not introduce correlation attributes."

    because that changes the meaning of the user's restriction.

    When splitting a coordinated restriction could alter or weaken its
    meaning, prefer preserving the original restriction as one sentence.

    Do not paraphrase a restriction in a way that makes it broader or
    narrower than the original statement.

    ====================
    AMBIGUITIES
    ====================

    If information required to fully specify the monitoring objective is
    missing, preserve that uncertainty in the `ambiguities` field.

    Do not resolve ambiguities yourself.

    Examples of task ambiguities include:

    - "abnormal number" with no numerical threshold;
    - "limited time window" with no duration;
    - "same source" when the scenario does not define how source should be
    represented;
    - a required protocol that cannot be identified from the supplied
    scenario.

    An ambiguity concerns information missing from the user's intended task.

    Do not classify missing external protocol semantics as a task ambiguity
    when the user has already stated the intended semantic concept.

    For example:

    "Detect a named protocol operation"

    provides the intended semantic concept.

    If a later component does not know which concrete protocol value
    corresponds to that operation, that is missing protocol knowledge rather
    than task underspecification.

    ====================
    CORRELATION REPRESENTATION RULE
    ====================

    When the monitoring objective requires events to share an abstract
    identity or origin, the representation of that correlation must be
    explicitly specified.

    In particular:

    If the scenario uses "same source" or an equivalent abstract source
    requirement, but neither the original scenario nor user clarifications
    identify the concrete representation of that source, you MUST record an
    ambiguity.

    For example:

    "requests from the same source"

    without an explicit mapping to a concrete observable identifier

    requires an ambiguity describing that the representation of "same
    source" has not been specified.

    The phrase "same source" by itself is not a concrete correlation key.

    Do not silently choose a protocol attribute to represent it.

    ====================
    USER CLARIFICATIONS
    ====================

    The scenario may include USER CLARIFICATIONS collected after an earlier
    interpretation.

    Treat those clarifications as authoritative additional information
    provided by the user.

    A clarification may:

    - add or refine a requirement;
    - add or refine a restriction;
    - resolve one or more previously identified ambiguities.

    When a clarification explicitly resolves an ambiguity:

    - incorporate the supplied information into the relevant requirement or
    restriction;
    - do not keep that ambiguity in the output.

    When a clarification resolves only part of an ambiguity:

    - incorporate only the information explicitly supplied;
    - preserve the unresolved part in the ambiguities field.

    Preserve the wording and semantic scope of explicit clarification
    constraints in the same way as constraints from the original scenario.

    Never extend a clarification beyond what the user explicitly stated.

    Do not infer additional values, mappings, thresholds, durations,
    protocol attributes, or protocol semantics from a clarification.

    ====================
    PROTOCOL IDENTIFIERS
    ====================

    Use only protocol identifiers contained in AVAILABLE PROTOCOLS.

    When the scenario explicitly names one of those protocols, include it.

    A common textual spelling may be normalized when the mapping is
    unambiguous.

    For example:

    "HTTP/2"

    may be normalized to:

    "http2"

    when `http2` is listed in AVAILABLE PROTOCOLS.

    Do not select a protocol merely because it appears plausible.

    If a protocol cannot be determined safely from the supplied scenario
    and clarifications, preserve that uncertainty rather than guessing.

    ====================
    DESCRIPTION
    ====================

    Produce a concise technical description of the monitoring objective.

    The description may normalize wording for clarity, but it must not:

    - add requirements;
    - remove explicit requirements;
    - remove explicit restrictions;
    - resolve ambiguities;
    - introduce unsupported protocol semantics.

    ====================
    EXPECTED BEHAVIOR
    ====================

    Populate expected_behavior only when the expected monitoring outcome can
    be stated from the original scenario and clarifications.

    Do not invent an expected behavior that adds monitoring conditions not
    explicitly supported by the input.

    It is acceptable to return null when no additional expected behavior is
    explicitly stated or safely derivable without adding requirements.

    ====================
    IDENTIFIER CONTROL
    ====================

    The scenario id and property_id are controlled externally.

    They are not part of your output.

    Do not invent or modify them.

    ====================
    OUTPUT RULES
    ====================

    Return only one JSON object matching the required schema.

    Do not include Markdown code fences.
    Do not include explanatory prose outside the JSON object.

    Before returning the JSON object, verify:

    1. every explicit positive monitoring requirement has been preserved;
    2. every explicit prohibition or limitation has been preserved;
    3. modifiers such as "additional", "only", "same", "exactly",
    "at least", and "at most" have retained their original scope;
    4. no missing value or mapping has been invented;
    5. resolved ambiguities have been removed;
    6. unresolved ambiguities remain explicitly listed.

    ====================
    TASK INTERPRETATION SKILL
    ====================

    {context.interpretation_skill}

    ====================
    AVAILABLE PROTOCOLS
    ====================

    {json.dumps(context.available_protocols, indent=2)}

    ====================
    REQUIRED OUTPUT SCHEMA
    ====================

    {json.dumps(output_schema, indent=2)}
    """.strip()

        user_content = f"""
    Interpret the following natural-language monitoring scenario together
    with any explicit clarifications subsequently supplied by the user.

    ====================
    ORIGINAL SCENARIO
    ====================

    {scenario.text}

    ====================
    USER CLARIFICATIONS
    ====================

    {json.dumps(scenario.clarifications, indent=2)}

    Extract:

    - description;
    - protocols;
    - monitoring_point, when explicitly available;
    - requirements;
    - restrictions;
    - expected_behavior;
    - ambiguities.

    Preserve all explicit positive requirements.

    Preserve all explicit negative constraints and prohibitions in
    `restrictions`.

    Preserve the semantic scope of qualifiers and modifiers.

    In particular, do not discard or weaken expressions such as:

    - "do not";
    - "must not";
    - "only";
    - "without";
    - "avoid";
    - "do not introduce";
    - "do not use";
    - "additional";
    - "same";
    - "exactly";
    - "at least";
    - "at most".

    For coordinated restrictions, preserve the original sentence when
    splitting it could change the scope of a modifier.

    For example:

    "Do not introduce additional procedure codes or correlation attributes."

    should preferably remain:

    "Do not introduce additional procedure codes or correlation attributes."

    It must not be transformed into a broader restriction such as:

    "Do not introduce correlation attributes."

    The USER CLARIFICATIONS are authoritative extensions of the original
    scenario.

    If a clarification explicitly resolves a previously missing threshold,
    duration, source representation, restriction, or other task requirement,
    incorporate that information into the structured task and remove only
    the corresponding resolved ambiguity.

    If a clarification resolves only part of an ambiguity, preserve any
    remaining unresolved information in `ambiguities`.

    Do not invent information that is absent from both the original scenario
    and the user clarifications.

    Before returning the result, verify that no explicit requirement,
    prohibition, modifier, or limitation from the original scenario or
    clarifications has been silently omitted or changed in meaning.

    Return only the JSON TaskInterpretation.
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

    def _parse_interpretation(
        self,
        content: str,
    ) -> TaskInterpretation:
        """
        Parse and validate the LLM interpretation.
        """

        json_content = (
            extract_interpretation_json(
                content
            )
        )

        try:
            data = json.loads(
                json_content
            )

        except json.JSONDecodeError as exc:
            raise TaskInterpretationError(
                "The task interpreter returned "
                "invalid JSON."
            ) from exc

        try:
            return (
                TaskInterpretation
                .model_validate(
                    data
                )
            )

        except ValidationError as exc:
            raise TaskInterpretationError(
                "The task interpreter response does "
                "not match the TaskInterpretation "
                "model."
            ) from exc

    def _build_refinement_messages(
        self,
        task: MonitoringTask,
        scenario: NaturalLanguageScenario,
        context: TaskInterpretationContext,
    ) -> list[dict[str, str]]:
        """
        Build instructions for extracting only the changes
        introduced by the latest user clarification.

        The existing MonitoringTask is authoritative and
        must not be reconstructed from scratch.
        """

        output_schema = (
            TaskClarificationUpdate
            .model_json_schema()
        )

        latest_clarification = (
            scenario.clarifications[-1]
        )

        task_data = task.model_dump(
            mode="json"
        )

        system_content = f"""
    You are a monitoring-task clarification interpreter.

    Your responsibility is to extract only the changes explicitly introduced
    by the latest user clarification.

    You are not reconstructing the complete monitoring task.

    The CURRENT MONITORING TASK is authoritative.

    Information not addressed by the clarification must remain unchanged.

    ====================
    UPDATE OPERATIONS
    ====================

    Use `requirement_updates` to update monitoring requirements.

    Each update contains:

    - `previous`;
    - `value`.

    Use:

    `previous = null`

    when the clarification introduces a genuinely new requirement.

    Use:

    `previous = "<exact existing requirement>"`

    when the clarification makes an existing requirement more precise.

    The `previous` value must be copied EXACTLY from the CURRENT MONITORING
    TASK requirements.

    Do not paraphrase `previous`.

    Example:

    Current requirement:

    "within a limited time window"

    Clarification:

    "Use a 5-second time window."

    Return:

    {{
    "previous": "within a limited time window",
    "value": "within 5 seconds"
    }}

    Do not keep both the vague and clarified versions when the clarification
    clearly replaces the vague requirement.

    ====================
    MULTIPLE REFINEMENTS
    ====================

    One clarification may refine multiple existing requirements.

    For example, if the task contains:

    - "detect an abnormal number of requests";
    - "within a limited time window";

    and the user clarifies:

    "More than 10 requests within 5 seconds."

    return two requirement updates:

    1. refine the abnormal-number requirement with the explicit threshold;
    2. refine the time-window requirement with the explicit duration.

    Do not merge unrelated requirements unnecessarily.

    ====================
    CORRELATION REFINEMENT
    ====================

    If the task contains an abstract correlation requirement such as:

    "from the same source"

    and the user explicitly defines which observable identifier represents that
    relationship, refine the existing requirement rather than adding a second
    parallel requirement.

    The concrete identifier must come from the user clarification.

    Do not invent a correlation representation.

    ====================
    RESTRICTION UPDATES
    ====================

    Use `restriction_updates` in the same way.

    When the clarification introduces a new restriction:

    `previous = null`

    When it explicitly refines an existing restriction:

    `previous` must exactly match the existing restriction.

    Preserve semantic modifiers such as:

    - only;
    - additional;
    - exactly;
    - at least;
    - at most;
    - same;
    - different.

    ====================
    RESOLVING AMBIGUITIES
    ====================

    Add an item to `resolved_ambiguities` only when the latest clarification
    directly provides the information missing from that ambiguity.

    Every item in `resolved_ambiguities` must be copied EXACTLY from CURRENT
    AMBIGUITIES.

    Do not paraphrase ambiguity text.

    If a clarification does not address an ambiguity, do not mark it resolved.

    ====================
    NEW AMBIGUITIES
    ====================

    Use `new_ambiguities` only when the clarification itself introduces a new
    unresolved requirement.

    Do not copy existing unresolved ambiguities into this field.

    ====================
    PROTOCOLS
    ====================

    Use only protocol identifiers contained in AVAILABLE PROTOCOLS.

    Do not infer a protocol merely because it appears plausible.

    ====================
    NO INVENTION
    ====================

    Do not invent:

    - thresholds;
    - durations;
    - protocol values;
    - protocol attributes;
    - correlation identifiers;
    - message meanings;
    - operation meanings;
    - enumerated-value meanings;
    - restrictions.

    Extract only information explicitly provided by the user clarification.

    ====================
    AVAILABLE PROTOCOLS
    ====================

    {json.dumps(context.available_protocols, indent=2)}

    ====================
    REQUIRED OUTPUT SCHEMA
    ====================

    {json.dumps(output_schema, indent=2)}

    Return only one JSON object matching TaskClarificationUpdate.

    Do not include Markdown.
    Do not include explanatory text.
    """.strip()

        user_content = f"""
    Apply the latest user clarification to the existing monitoring task.

    ====================
    ORIGINAL SCENARIO
    ====================

    {scenario.text}

    ====================
    CURRENT MONITORING TASK
    ====================

    {json.dumps(task_data, indent=2)}

    ====================
    CURRENT REQUIREMENTS
    ====================

    {json.dumps(task.requirements, indent=2)}

    ====================
    CURRENT RESTRICTIONS
    ====================

    {json.dumps(task.restrictions, indent=2)}

    ====================
    CURRENT AMBIGUITIES
    ====================

    {json.dumps(task.ambiguities, indent=2)}

    ====================
    LATEST USER CLARIFICATION
    ====================

    {latest_clarification}

    Extract only the changes introduced by this clarification.

    When the clarification makes an existing requirement more precise, use a
    replacement update:

    - copy the existing requirement exactly into `previous`;
    - put the clarified requirement into `value`.

    When the clarification introduces genuinely new information that does not
    replace an existing requirement, use:

    `previous = null`.

    For every resolved ambiguity, copy the ambiguity text exactly from
    CURRENT AMBIGUITIES.

    Do not reconstruct the complete task.

    Do not modify information unrelated to the clarification.

    Return only the JSON TaskClarificationUpdate.
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

    def _parse_clarification_update(
        self,
        content: str,
    ) -> TaskClarificationUpdate:
        """
        Parse one structured clarification delta.
        """

        json_content = (
            extract_interpretation_json(
                content
            )
        )

        try:
            data = json.loads(
                json_content
            )

        except json.JSONDecodeError as exc:
            raise TaskInterpretationError(
                "The task clarification interpreter "
                "returned invalid JSON."
            ) from exc

        try:
            return (
                TaskClarificationUpdate
                .model_validate(
                    data
                )
            )

        except ValidationError as exc:
            raise TaskInterpretationError(
                "The task clarification response does "
                "not match TaskClarificationUpdate."
            ) from exc

    def refine(
        self,
        task: MonitoringTask,
        scenario: NaturalLanguageScenario,
    ) -> TaskInterpretationResult:
        """
        Apply the latest explicit user clarification to an
        existing MonitoringTask.

        Existing information is preserved deterministically.

        The LLM produces only explicit update operations.
        """

        if not scenario.clarifications:
            return TaskInterpretationResult(
                scenario_id=scenario.id,
                task=task,
                model=self.client.config.model,
                metadata={
                    "refinement_skipped":
                        True,
                },
            )

        context = (
            self.context_builder.build()
        )

        messages = (
            self._build_refinement_messages(
                task=task,
                scenario=scenario,
                context=context,
            )
        )

        response = self.client.complete(
            messages
        )

        update = (
            self._parse_clarification_update(
                response.content
            )
        )

        # --------------------------------------------------
        # Ambiguity resolution
        # --------------------------------------------------

        valid_resolved = [
            ambiguity
            for ambiguity
            in update.resolved_ambiguities
            if ambiguity in task.ambiguities
        ]

        ignored_resolved = [
            ambiguity
            for ambiguity
            in update.resolved_ambiguities
            if ambiguity not in task.ambiguities
        ]

        resolved_set = set(
            valid_resolved
        )

        remaining_ambiguities = [
            ambiguity
            for ambiguity
            in task.ambiguities
            if ambiguity not in resolved_set
        ]

        remaining_ambiguities = (
            _deduplicate(
                [
                    *remaining_ambiguities,
                    *update.new_ambiguities,
                ]
            )
        )

        # --------------------------------------------------
        # Canonical requirements
        # --------------------------------------------------

        (
            updated_requirements,
            applied_requirement_updates,
            ignored_requirement_updates,
        ) = _apply_text_updates(
            task.requirements,
            update.requirement_updates,
        )

        # --------------------------------------------------
        # Canonical restrictions
        # --------------------------------------------------

        (
            updated_restrictions,
            applied_restriction_updates,
            ignored_restriction_updates,
        ) = _apply_text_updates(
            task.restrictions,
            update.restriction_updates,
        )

        # --------------------------------------------------
        # Protocol additions
        # --------------------------------------------------

        valid_protocols_to_add = [
            protocol
            for protocol
            in update.protocols_to_add
            if protocol
            in context.available_protocols
        ]

        # --------------------------------------------------
        # Provenance
        # --------------------------------------------------

        metadata = dict(
            task.metadata
        )

        input_metadata = dict(
            metadata.get(
                "input",
                {},
            )
        )

        input_metadata[
            "clarifications"
        ] = list(
            scenario.clarifications
        )

        metadata[
            "input"
        ] = input_metadata

        refinement_history = list(
            metadata.get(
                "clarification_refinement_history",
                [],
            )
        )

        refinement_history.append(
            {
                "clarification":
                    scenario.clarifications[-1],

                "requirement_updates":
                    applied_requirement_updates,

                "ignored_requirement_updates":
                    ignored_requirement_updates,

                "restriction_updates":
                    applied_restriction_updates,

                "ignored_restriction_updates":
                    ignored_restriction_updates,

                "ambiguities_resolved":
                    valid_resolved,

                "ignored_resolved_ambiguities":
                    ignored_resolved,

                "new_ambiguities":
                    update.new_ambiguities,

                "protocols_added":
                    valid_protocols_to_add,

                "model":
                    self.client.config.model,

                "provider_model":
                    response.model,
            }
        )

        metadata[
            "clarification_refinement_history"
        ] = refinement_history

        # --------------------------------------------------
        # Canonical task
        # --------------------------------------------------

        updated_task = task.model_copy(
            update={
                "protocols":
                    _deduplicate(
                        [
                            *task.protocols,
                            *valid_protocols_to_add,
                        ]
                    ),

                "monitoring_point": (
                    update.monitoring_point
                    if update.monitoring_point
                    is not None
                    else task.monitoring_point
                ),

                "requirements":
                    updated_requirements,

                "restrictions":
                    updated_restrictions,

                "expected_behavior": (
                    update.expected_behavior
                    if update.expected_behavior
                    is not None
                    else task.expected_behavior
                ),

                "ambiguities":
                    remaining_ambiguities,

                "assumptions":
                    list(
                        task.assumptions
                    ),

                "metadata":
                    metadata,
            }
        )

        return TaskInterpretationResult(
            scenario_id=scenario.id,
            task=updated_task,
            model=self.client.config.model,
            metadata={
                "provider_model":
                    response.model,

                "usage":
                    response.usage,

                "refinement":
                    True,
            },
        )

    def interpret(
        self,
        scenario: NaturalLanguageScenario,
    ) -> TaskInterpretationResult:
        """
        Interpret one natural-language scenario and
        construct the canonical MonitoringTask.
        """

        context = (
            self.context_builder.build()
        )

        messages = self._build_messages(
            scenario=scenario,
            context=context,
        )

        response = self.client.complete(
            messages
        )

        interpretation = (
            self._parse_interpretation(
                response.content
            )
        )

        task = MonitoringTask(
            id=scenario.id,
            property_id=(
                scenario.property_id
            ),
            description=(
                interpretation.description
            ),
            protocols=(
                interpretation.protocols
            ),
            monitoring_point=(
                interpretation.monitoring_point
            ),
            requirements=(
                interpretation.requirements
            ),
            restrictions=(
                interpretation.restrictions
            ),
            expected_behavior=(
                interpretation.expected_behavior
            ),
            ambiguities=(
                interpretation.ambiguities
            ),
            metadata={
                **scenario.metadata,
                "input": {
                    "mode": "natural_language",
                    "original_text": scenario.text,
                    "clarifications": list(
                        scenario.clarifications
                    ),
                },
            },
        )

        return TaskInterpretationResult(
            scenario_id=scenario.id,
            task=task,
            model=self.client.config.model,
            metadata={
                "provider_model":
                    response.model,

                "usage":
                    response.usage,
            },
        )