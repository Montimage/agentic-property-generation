from property_agent.models import (
    NaturalLanguageScenario,
    NaturalLanguageWorkflowResult,
    NaturalLanguageWorkflowStatus,
)

from .graph import (
    PropertyWorkflow,
)

from .intake_graph import (
    TaskIntakeWorkflow,
)


class NaturalLanguagePropertyWorkflow:
    """
    Integration facade joining:

    1. natural-language task intake;
    2. clarification and authorized assumptions;
    3. the existing property-generation
       workflow.

    The PropertyWorkflow remains unchanged.
    """

    def __init__(
        self,
        intake_workflow: TaskIntakeWorkflow,
        property_workflow: PropertyWorkflow,
    ):
        self.intake_workflow = (
            intake_workflow
        )

        self.property_workflow = (
            property_workflow
        )

    @staticmethod
    def _property_thread_id(
        thread_id: str,
    ) -> str:
        """
        Use a separate checkpoint thread.

        Intake and property-generation graphs therefore
        cannot accidentally share checkpoint state.
        """

        return (
            f"{thread_id}:property"
        )

    @staticmethod
    def _extract_interrupt_payload(
        intake_result,
    ) -> dict | None:
        """
        Extract the first LangGraph interrupt payload
        returned by the intake workflow.
        """

        interrupts = intake_result.get(
            "__interrupt__"
        )

        if not interrupts:
            return None

        interrupt_item = (
            interrupts[0]
        )

        if hasattr(
            interrupt_item,
            "value",
        ):
            return interrupt_item.value

        # Useful for test doubles or alternate
        # serialization.
        if isinstance(
            interrupt_item,
            dict,
        ):
            return interrupt_item

        raise RuntimeError(
            "Unsupported task-clarification "
            "interrupt payload."
        )

    def _handle_intake_result(
        self,
        intake_result,
        thread_id: str,
    ) -> NaturalLanguageWorkflowResult:
        """
        Convert intake state into the corresponding
        public natural-language workflow result.

        The property-generation workflow executes only when intake has produced
        a complete MonitoringTask.
        """

        clarification_payload = (
            self._extract_interrupt_payload(
                intake_result
            )
        )

        # --------------------------------------------------
        # Waiting for user clarification
        # --------------------------------------------------

        if clarification_payload is not None:
            return NaturalLanguageWorkflowResult(
                status=(
                    NaturalLanguageWorkflowStatus
                    .CLARIFICATION_REQUIRED
                ),
                thread_id=thread_id,
                task=intake_result.get(
                    "task"
                ),
                clarification_payload=(
                    clarification_payload
                ),
                metadata={
                    "clarification_round":
                        intake_result.get(
                            "clarification_round",
                            0,
                        ),

                    "intake_terminal_reason":
                        intake_result.get(
                            "terminal_reason"
                        ),
                },
            )

        terminal_reason = (
            intake_result.get(
                "terminal_reason"
            )
        )

        # --------------------------------------------------
        # Explicit user cancellation
        # --------------------------------------------------

        if (
            terminal_reason
            == "clarification_cancelled"
        ):
            return NaturalLanguageWorkflowResult(
                status=(
                    NaturalLanguageWorkflowStatus
                    .CANCELLED
                ),
                thread_id=thread_id,
                task=intake_result.get(
                    "task"
                ),
                metadata={
                    "terminal_reason":
                        terminal_reason,

                    "clarification_round":
                        intake_result.get(
                            "clarification_round",
                            0,
                        ),
                },
            )

        # --------------------------------------------------
        # Intake could not produce a complete task
        # --------------------------------------------------

        if not intake_result.get(
            "complete",
            False,
        ):
            return NaturalLanguageWorkflowResult(
                status=(
                    NaturalLanguageWorkflowStatus
                    .BLOCKED
                ),
                thread_id=thread_id,
                task=intake_result.get(
                    "task"
                ),
                metadata={
                    "terminal_reason":
                        terminal_reason,

                    "clarification_round":
                        intake_result.get(
                            "clarification_round",
                            0,
                        ),
                },
            )

        # --------------------------------------------------
        # Task ready -> existing property-generation workflow
        # --------------------------------------------------

        task = intake_result[
            "task"
        ]

        property_thread_id = (
            self._property_thread_id(
                thread_id
            )
        )

        property_result = (
            self.property_workflow.run(
                task=task,
                thread_id=(
                    property_thread_id
                ),
            )
        )

        return NaturalLanguageWorkflowResult(
            status=(
                NaturalLanguageWorkflowStatus
                .COMPLETED
            ),
            thread_id=thread_id,
            task=task,
            property_result=(
                property_result
            ),
            metadata={
                "intake_terminal_reason":
                    terminal_reason,

                "clarification_round":
                    intake_result.get(
                        "clarification_round",
                        0,
                    ),

                "property_thread_id":
                    property_thread_id,

                "assumption_count":
                    len(
                        task.assumptions
                    ),

                "clarification_count":
                    len(
                        intake_result[
                            "scenario"
                        ].clarifications
                    ),
            },
        )

    def start(
        self,
        scenario: NaturalLanguageScenario,
        thread_id: str,
    ) -> NaturalLanguageWorkflowResult:
        """
        Start a new natural-language monitoring
        workflow.
        """

        intake_result = (
            self.intake_workflow.start(
                scenario=scenario,
                thread_id=thread_id,
            )
        )

        return self._handle_intake_result(
            intake_result=(
                intake_result
            ),
            thread_id=thread_id,
        )

    def resume(
        self,
        clarification,
        thread_id: str,
    ) -> NaturalLanguageWorkflowResult:
        """
        Resume an intake workflow waiting for a user
        clarification decision.

        `clarification` may contain:

        - clarify;
        - assume_remaining;
        - cancel.
        """

        intake_result = (
            self.intake_workflow.resume(
                clarification=(
                    clarification
                ),
                thread_id=thread_id,
            )
        )

        return self._handle_intake_result(
            intake_result=(
                intake_result
            ),
            thread_id=thread_id,
        )