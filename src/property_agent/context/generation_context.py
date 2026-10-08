from dataclasses import dataclass
from typing import Any

from property_agent.knowledge import (
    has_protocol_knowledge,
    load_protocol_attributes,
)

from property_agent.models import (
    MonitoringTask,
    RetrievalResult,
)

from property_agent.skills import (
    load_skill,
    load_skill_resource,
)


class MissingProtocolKnowledgeError(
    RuntimeError
):
    pass


@dataclass
class GenerationContext:
    generation_skill: str

    property_format: str

    restrictions: str

    common_errors: str

    protocol_knowledge: dict[
        str,
        dict[str, Any],
    ]

    retrieval_result: (
        RetrievalResult | None
    ) = None


class GenerationContextBuilder:
    def __init__(
        self,
        strict_protocol_knowledge: bool = True,
    ):
        self.strict_protocol_knowledge = (
            strict_protocol_knowledge
        )

    def build(
        self,
        task: MonitoringTask,
        retrieval_result: (
            RetrievalResult | None
        ) = None,
    ) -> GenerationContext:

        generation_skill = load_skill(
            "property_generation"
        )

        property_format = (
            load_skill_resource(
                "property_generation",
                "property_format.md",
            )
        )

        restrictions = (
            load_skill_resource(
                "property_generation",
                "restrictions.md",
            )
        )

        common_errors = (
            load_skill_resource(
                "property_generation",
                "common_errors.md",
            )
        )

        protocol_knowledge = {}

        for protocol in task.protocols:

            normalized = protocol.lower()

            if not has_protocol_knowledge(
                normalized
            ):
                if (
                    self
                    .strict_protocol_knowledge
                ):
                    raise (
                        MissingProtocolKnowledgeError(
                            "Missing protocol "
                            "knowledge for "
                            f"'{protocol}'."
                        )
                    )

                continue

            protocol_knowledge[
                normalized
            ] = load_protocol_attributes(
                normalized
            )

        return GenerationContext(
            generation_skill=(
                generation_skill
            ),
            property_format=(
                property_format
            ),
            restrictions=restrictions,
            common_errors=common_errors,
            protocol_knowledge=(
                protocol_knowledge
            ),
            retrieval_result=(
                retrieval_result
            ),
        )