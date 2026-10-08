from dataclasses import dataclass
from typing import Any

from property_agent.knowledge import (
    has_protocol_knowledge,
    load_protocol_attributes,
)

from property_agent.models import (
    MonitoringTask,
)

from property_agent.skills import (
    load_skill,
    load_skill_resource,
)


@dataclass
class RepairContext:
    """
    Instructions and verified knowledge available to
    the property repair agent.
    """

    repair_skill: str

    property_format: str

    restrictions: str

    common_errors: str

    protocol_attributes: dict[
        str,
        dict[str, Any],
    ]

    missing_attribute_knowledge: list[str]


class RepairContextBuilder:
    """
    Build the task-specific context used for one repair
    attempt.
    """

    def build(
        self,
        task: MonitoringTask,
    ) -> RepairContext:

        repair_skill = load_skill(
            "property_repair"
        )

        property_format = load_skill_resource(
            "property_generation",
            "property_format.md",
        )

        restrictions = load_skill_resource(
            "property_generation",
            "restrictions.md",
        )

        common_errors = load_skill_resource(
            "property_generation",
            "common_errors.md",
        )

        protocol_attributes = {}

        missing_attribute_knowledge = []

        for protocol in task.protocols:

            normalized = protocol.lower()

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

        return RepairContext(
            repair_skill=repair_skill,
            property_format=property_format,
            restrictions=restrictions,
            common_errors=common_errors,
            protocol_attributes=protocol_attributes,
            missing_attribute_knowledge=(
                missing_attribute_knowledge
            ),
        )