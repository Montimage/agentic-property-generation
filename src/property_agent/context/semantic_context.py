from dataclasses import dataclass
from typing import Any

from property_agent.knowledge import (
    has_protocol_knowledge,
    load_protocol_attributes,
)

from property_agent.models import (
    MonitoringTask,
    GeneratedProperty,
)

from property_agent.skills import (
    load_skill,
)

from property_agent.tools.mmt_static_validator import (
    extract_referenced_protocols,
)


@dataclass
class SemanticReviewContext:
    """
    Knowledge and instructions available to the
    semantic reviewer.
    """

    validation_skill: str

    protocol_attributes: dict[
        str,
        dict[str, Any],
    ]

    missing_attribute_knowledge: list[str]


class SemanticReviewContextBuilder:
    """
    Build task-specific context for semantic validation.

    Missing semantic knowledge does not prevent semantic
    review. Instead, the reviewer is informed explicitly
    so that uncertainty can be reported as KNOWLEDGE_MISSING.
    """

    def build(
        self,
        task: MonitoringTask,
        generated_property: GeneratedProperty | None = None,
    ) -> SemanticReviewContext:

        validation_skill = load_skill(
            "semantic_validation"
        )

        protocol_attributes = {}

        missing_attribute_knowledge = []

        required_protocols = {
            protocol.lower()
            for protocol in task.protocols
        }

        if generated_property is not None:
            required_protocols.update(
                extract_referenced_protocols(
                    generated_property.xml
                )
            )

        for normalized in sorted(
            required_protocols
        ):
            if has_protocol_knowledge(
                normalized
            ):
                protocol_attributes[
                    normalized
                ] = load_protocol_attributes(
                    normalized
                )
            else:
                missing_attribute_knowledge.append(
                    normalized
                )

        return SemanticReviewContext(
            validation_skill=validation_skill,
            protocol_attributes=protocol_attributes,
            missing_attribute_knowledge=(
                missing_attribute_knowledge
            ),
        )