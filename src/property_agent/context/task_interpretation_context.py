from dataclasses import dataclass

from property_agent.knowledge import (
    list_protocols_with_attribute_knowledge,
)

from property_agent.skills import (
    load_skill,
)


@dataclass
class TaskInterpretationContext:
    """
    Stable context supplied to the natural-language
    task interpreter.
    """

    interpretation_skill: str

    available_protocols: list[str]


class TaskInterpretationContextBuilder:
    """
    Build deterministic context for task
    interpretation.
    """

    def build(
        self,
    ) -> TaskInterpretationContext:

        return TaskInterpretationContext(
            interpretation_skill=load_skill(
                "task_interpretation"
            ),
            available_protocols=(
                list_protocols_with_attribute_knowledge()
            ),
        )