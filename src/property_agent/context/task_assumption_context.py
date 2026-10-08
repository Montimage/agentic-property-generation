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
)


@dataclass
class TaskAssumptionContext:
    assumption_skill: str

    protocol_attributes: dict[
        str,
        Any,
    ]


class TaskAssumptionContextBuilder:
    """
    Build task-specific knowledge used when resolving
    user-authorized assumptions.
    """

    def build(
        self,
        task: MonitoringTask,
    ) -> TaskAssumptionContext:

        protocol_attributes = {}

        for protocol in task.protocols:
            if has_protocol_knowledge(
                protocol
            ):
                protocol_attributes[
                    protocol
                ] = load_protocol_attributes(
                    protocol
                )

        return TaskAssumptionContext(
            assumption_skill=load_skill(
                "task_assumption"
            ),
            protocol_attributes=(
                protocol_attributes
            ),
        )