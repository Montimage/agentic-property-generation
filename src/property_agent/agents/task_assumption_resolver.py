import json

from pydantic import ValidationError

from property_agent.context import (
    TaskAssumptionContext,
    TaskAssumptionContextBuilder,
)

from property_agent.llm import (
    LLMClient,
)

from property_agent.models import (
    MonitoringTask,
    TaskAssumptionResolution,
)


class TaskAssumptionError(
    RuntimeError
):
    """
    Raised when authorized assumption resolution
    cannot produce the expected structured result.
    """


def extract_assumption_json(
    content: str,
) -> str:

    content = content.strip()

    start = content.find("{")
    end = content.rfind("}")

    if (
        start == -1
        or end == -1
        or end < start
    ):
        raise TaskAssumptionError(
            "The assumption resolver response "
            "does not contain a valid JSON object."
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
    Apply assumption-driven requirement updates
    deterministically.

    An existing requirement can be replaced only when
    `previous` exactly matches a current canonical
    requirement.

    This prevents the assumption resolver from silently
    rewriting unrelated task requirements.
    """

    result = list(
        current
    )

    applied = []
    ignored = []

    for update in updates:

        # ----------------------------------------------
        # New requirement introduced by an authorized
        # assumption.
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
        # Refinement of an existing vague requirement.
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


class TaskAssumptionResolver:
    """
    Resolve remaining task-level ambiguities after
    explicit user authorization.

    This agent does not resolve missing factual
    protocol knowledge.
    """

    def __init__(
        self,
        client: LLMClient,
        context_builder: (
            TaskAssumptionContextBuilder
            | None
        ) = None,
    ):
        self.client = client

        self.context_builder = (
            context_builder
            or TaskAssumptionContextBuilder()
        )

    def _build_messages(
        self,
        task: MonitoringTask,
        context: TaskAssumptionContext,
    ) -> list[dict[str, str]]:

        output_schema = (
            TaskAssumptionResolution
            .model_json_schema()
        )

        system_content = f"""
You are a monitoring-task assumption resolver.

The user has explicitly authorized you to make the minimum assumptions
necessary to resolve the CURRENTLY LISTED task-level ambiguities.

You are not a monitoring-property generator.

Do not generate XML.

====================
ASSUMPTION SCOPE
====================

Authorization to make assumptions applies ONLY to ambiguities currently
listed in the MonitoringTask.

Do not modify, reinterpret, strengthen, weaken, or replace requirements that
are already explicitly specified and are unrelated to those ambiguities.

For example, if the task explicitly requires:

"two events"

and the only unresolved ambiguity concerns the duration of a time window,
you MUST preserve:

"two events"

exactly in meaning.

You must not change it into:

"more than two events",
"at least two events",
"three events",

or any other different event-count requirement.

Every assumption must correspond directly to one currently unresolved
ambiguity.

Do not introduce assumptions for information that is already explicitly
specified.

====================
REQUIREMENT UPDATES
====================

Use `requirement_updates` to express only requirement changes caused by an
authorized assumption.

Each update contains:

- `previous`;
- `value`.

When the assumption makes an existing vague requirement concrete, set
`previous` to the EXACT existing requirement text and set `value` to the
concrete operative requirement.

For example:

Current requirement:

"short time window"

Authorized assumption:

"Treat 10 seconds as the short-time window duration."

Return:

{{
  "previous": "short time window",
  "value": "within 10 seconds"
}}

The `previous` value must be copied exactly from the CURRENT REQUIREMENTS.

Do not paraphrase `previous`.

Do not preserve both the vague and concrete requirement when the assumption
clearly resolves the vague requirement.

Use:

`previous = null`

only when resolving the ambiguity genuinely requires a new operative
requirement and there is no existing requirement that should be refined.

Do not use requirement updates to alter unrelated explicit requirements.

====================
ASSUMPTIONS
====================

Every inferred choice must be recorded explicitly in `assumptions`.

The assumption text must make clear that the value was assumed after user
authorization rather than originally supplied by the user.

Make only the minimum assumption necessary to resolve the ambiguity.

====================
RESOLVING AMBIGUITIES
====================

Use `resolved_ambiguities` only for ambiguities that can be safely resolved
by an authorized task-level assumption.

Every item in `resolved_ambiguities` must be copied EXACTLY from the current
MonitoringTask ambiguities.

Do not paraphrase ambiguity text.

Do not mark an ambiguity as resolved unless the corresponding assumption and
operative requirement are sufficient to resolve it.

If an ambiguity cannot safely be resolved, omit it from
`resolved_ambiguities`.

It will remain unresolved in the canonical task.

====================
SAFE TASK-LEVEL ASSUMPTIONS
====================

You may make minimal task-level operational choices such as:

- a numerical threshold when the ambiguity explicitly concerns an undefined
  threshold;
- a time-window duration when the ambiguity explicitly concerns an undefined
  duration;
- another operational parameter whose choice does not require unavailable
  factual protocol knowledge.

Do not alter unrelated requirements while resolving such ambiguities.

====================
PROTOCOL ATTRIBUTE KNOWLEDGE
====================

Use only protocol attributes present in the supplied protocol attribute
knowledge.

The existence of an attribute does not establish the semantic meaning of a
particular protocol value.

====================
DO NOT INVENT FACTUAL PROTOCOL SEMANTICS
====================

Do not invent:

- procedure-code meanings;
- message-code meanings;
- operation identifiers;
- protocol-value meanings;
- state values;
- protocol attributes;
- correlation mappings requiring factual protocol knowledge;
- any external protocol fact absent from the supplied knowledge.

If resolving an ambiguity would require inventing unavailable factual
protocol knowledge, do not resolve that ambiguity.

Do not create an assumption merely because a technical choice appears
plausible.

====================
PRESERVATION CHECK
====================

Before returning the result, verify:

1. every assumption corresponds to a currently listed ambiguity;
2. no explicit unrelated requirement has changed meaning;
3. every `previous` value exactly matches a current requirement;
4. every resolved ambiguity exactly matches a current ambiguity;
5. no factual protocol semantics have been invented;
6. only the minimum necessary assumptions have been made.

====================
ASSUMPTION RESOLUTION SKILL
====================

{context.assumption_skill}

====================
AVAILABLE PROTOCOL ATTRIBUTE KNOWLEDGE
====================

{json.dumps(context.protocol_attributes, indent=2)}

====================
REQUIRED OUTPUT SCHEMA
====================

{json.dumps(output_schema, indent=2)}

Return only one JSON object matching TaskAssumptionResolution.

Do not include Markdown.
Do not include explanatory text.
""".strip()

        task_data = task.model_dump(
            mode="json"
        )

        user_content = f"""
Resolve only the currently listed ambiguities in this monitoring task.

The user has explicitly authorized minimal task-level assumptions.

====================
CURRENT MONITORING TASK
====================

{json.dumps(task_data, indent=2)}

====================
CURRENT REQUIREMENTS
====================

{json.dumps(task.requirements, indent=2)}

====================
CURRENT AMBIGUITIES
====================

{json.dumps(task.ambiguities, indent=2)}

Preserve every explicit requirement that is unrelated to an ambiguity.

Do not change an explicit requirement merely because assumptions have been
authorized.

For each safely resolved ambiguity:

- record the inferred choice in `assumptions`;
- refine the corresponding vague requirement using `requirement_updates`
  when applicable;
- copy the resolved ambiguity exactly into `resolved_ambiguities`.

If an ambiguity cannot safely be resolved without inventing factual protocol
knowledge, leave it unresolved by omitting it from `resolved_ambiguities`.

Make only the minimum assumptions required.

Return only the JSON TaskAssumptionResolution.
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

    def _parse_resolution(
        self,
        content: str,
    ) -> TaskAssumptionResolution:

        json_content = (
            extract_assumption_json(
                content
            )
        )

        try:
            data = json.loads(
                json_content
            )

        except json.JSONDecodeError as exc:
            raise TaskAssumptionError(
                "The assumption resolver returned "
                "invalid JSON."
            ) from exc

        try:
            return (
                TaskAssumptionResolution
                .model_validate(
                    data
                )
            )

        except ValidationError as exc:
            raise TaskAssumptionError(
                "The assumption resolver response "
                "does not match the expected model."
            ) from exc

    def resolve(
        self,
        task: MonitoringTask,
    ) -> MonitoringTask:
        """
        Resolve task-level ambiguities and return an
        updated canonical MonitoringTask.

        Existing requirements are preserved
        deterministically. The LLM supplies only
        authorized assumption-driven updates.
        """

        if not task.ambiguities:
            return task

        context = (
            self.context_builder.build(
                task
            )
        )

        messages = self._build_messages(
            task=task,
            context=context,
        )

        response = self.client.complete(
            messages
        )

        resolution = (
            self._parse_resolution(
                response.content
            )
        )

        # --------------------------------------------------
        # Apply requirement updates deterministically.
        #
        # Existing requirements can only be replaced when
        # the resolver references them exactly.
        # --------------------------------------------------

        (
            updated_requirements,
            applied_requirement_updates,
            ignored_requirement_updates,
        ) = _apply_text_updates(
            task.requirements,
            resolution.requirement_updates,
        )

        # --------------------------------------------------
        # Only currently existing ambiguities can be
        # resolved.
        # --------------------------------------------------

        valid_resolved = [
            ambiguity
            for ambiguity
            in resolution.resolved_ambiguities
            if ambiguity in task.ambiguities
        ]

        ignored_resolved = [
            ambiguity
            for ambiguity
            in resolution.resolved_ambiguities
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

        # --------------------------------------------------
        # Preserve provenance.
        # --------------------------------------------------

        metadata = dict(
            task.metadata
        )

        assumption_history = list(
            metadata.get(
                "assumption_resolution_history",
                []
            )
        )

        assumption_history.append(
            {
                "authorized":
                    True,

                "requirements_updated":
                    applied_requirement_updates,

                "ignored_requirement_updates":
                    ignored_requirement_updates,

                "assumptions_added":
                    resolution.assumptions,

                "ambiguities_resolved":
                    valid_resolved,

                "ignored_resolved_ambiguities":
                    ignored_resolved,

                "model":
                    self.client.config.model,

                "provider_model":
                    response.model,
            }
        )

        metadata[
            "assumption_resolution_history"
        ] = assumption_history

        metadata[
            "assumption_resolution"
        ] = {
            "authorized":
                True,

            "model":
                self.client.config.model,

            "provider_model":
                response.model,
        }

        return task.model_copy(
            update={
                "requirements":
                    updated_requirements,

                "assumptions":
                    _deduplicate(
                        [
                            *task.assumptions,
                            *resolution.assumptions,
                        ]
                    ),

                "ambiguities":
                    remaining_ambiguities,

                "metadata":
                    metadata,
            }
        )