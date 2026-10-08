from typing import Literal

from langgraph.checkpoint.memory import (
    InMemorySaver,
)
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.types import (
    Command,
    interrupt,
)

from property_agent.agents import (
    TaskInterpreter,
    TaskAssumptionResolver,
)
from property_agent.models import (
    NaturalLanguageScenario,
    ClarificationAction,
    TaskClarificationResponse,
)

from .intake_state import (
    TaskIntakeState,
)


class TaskIntakeWorkflow:
    """
    Natural-language monitoring-task intake workflow.

    Responsibilities:

    1. interpret a natural-language scenario;
    2. detect unresolved task ambiguities;
    3. ask the user for clarification;
    4. reinterpret using the user's clarification;
    5. repeat until the task is sufficiently specified
       or the clarification limit is reached.

    Property generation is intentionally outside this
    workflow.
    """

    def __init__(
        self,
        task_interpreter: TaskInterpreter,
        assumption_resolver: (
            TaskAssumptionResolver | None
        ) = None,
        max_clarification_rounds: int = 3,
        checkpointer=None,
    ):
        if max_clarification_rounds < 0:
            raise ValueError(
                "max_clarification_rounds must "
                "be >= 0."
            )

        self.task_interpreter = (
            task_interpreter
        )

        self.max_clarification_rounds = (
            max_clarification_rounds
        )

        self.assumption_resolver = (
            assumption_resolver
        )

        self.checkpointer = (
            checkpointer
            or InMemorySaver()
        )

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(
            TaskIntakeState
        )

        builder.add_node(
            "interpret_task",
            self._interpret_task,
        )

        builder.add_node(
            "clarify_task",
            self._clarify_task,
        )

        builder.add_node(
            "apply_clarification",
            self._apply_clarification,
        )

        builder.add_node(
            "finalize_complete",
            self._finalize_complete,
        )

        builder.add_node(
            "finalize_blocked",
            self._finalize_blocked,
        )

        builder.add_node(
            "resolve_assumptions",
            self._resolve_assumptions,
        )

        builder.add_node(
            "finalize_cancelled",
            self._finalize_cancelled,
        )

        builder.add_edge(
            START,
            "interpret_task",
        )

        builder.add_conditional_edges(
            "interpret_task",
            self._route_after_interpretation,
            {
                "complete":
                    "finalize_complete",

                "assume":
                    "resolve_assumptions",

                "clarify":
                    "clarify_task",

                "blocked":
                    "finalize_blocked",
            },
        )

        builder.add_edge(
            "clarify_task",
            "apply_clarification",
        )

        builder.add_conditional_edges(
            "apply_clarification",
            self._route_after_user_decision,
            {
                "reinterpret":
                    "interpret_task",

                "cancel":
                    "finalize_cancelled",
            },
        )

        builder.add_conditional_edges(
            "resolve_assumptions",
            self._route_after_assumptions,
            {
                "complete":
                    "finalize_complete",

                "blocked":
                    "finalize_blocked",
            },
        )

        builder.add_edge(
            "finalize_cancelled",
            END,
        )

        builder.add_edge(
            "finalize_complete",
            END,
        )

        builder.add_edge(
            "finalize_blocked",
            END,
        )

        return builder.compile(
            checkpointer=self.checkpointer
        )

    def _interpret_task(
        self,
        state: TaskIntakeState,
    ) -> dict:
        """
        Interpret the initial natural-language scenario or
        refine the existing canonical task after explicit
        user clarification.

        Initial scenario:
            full interpretation

        Later clarification:
            delta-based refinement preserving existing task
        """

        scenario = state[
            "scenario"
        ]

        current_task = state.get(
            "task"
        )

        # --------------------------------------------------
        # Initial interpretation
        # --------------------------------------------------

        if current_task is None:
            result = (
                self.task_interpreter
                .interpret(
                    scenario
                )
            )

        else:
            # Determine whether the scenario contains a
            # clarification that has not yet been applied
            # to the canonical task.
            task_input_metadata = (
                current_task
                .metadata
                .get(
                    "input",
                    {}
                )
            )

            applied_clarifications = (
                task_input_metadata.get(
                    "clarifications",
                    []
                )
            )

            has_new_clarification = (
                len(
                    scenario.clarifications
                )
                >
                len(
                    applied_clarifications
                )
            )

            if has_new_clarification:

                # Production TaskInterpreter supports the
                # refinement API.
                #
                # The fallback keeps simple test doubles
                # compatible with the workflow.
                if hasattr(
                    self.task_interpreter,
                    "refine",
                ):
                    result = (
                        self.task_interpreter
                        .refine(
                            task=current_task,
                            scenario=scenario,
                        )
                    )

                else:
                    result = (
                        self.task_interpreter
                        .interpret(
                            scenario
                        )
                    )

            else:
                # No new explicit information was supplied.
                #
                # This occurs, for example, when the user
                # chooses assume_remaining without adding
                # clarification text. Keep the canonical
                # task unchanged so the assumption resolver
                # can operate on the remaining ambiguities.
                return {
                    "task":
                        current_task,

                    "complete":
                        False,

                    "terminal_reason":
                        None,
                }

        return {
            "interpretation_result":
                result,

            "task":
                result.task,

            "complete":
                False,

            "terminal_reason":
                None,
        }

    def _route_after_interpretation(
        self,
        state: TaskIntakeState,
    ) -> Literal[
        "complete",
        "assume",
        "clarify",
        "blocked",
    ]:
        task = state["task"]

        if not task.ambiguities:
            return "complete"

        # The user already explicitly authorized the
        # system to resolve remaining task ambiguities.
        if state.get(
            "assume_remaining",
            False,
        ):
            return "assume"

        clarification_round = (
            state.get(
                "clarification_round",
                0,
            )
        )

        max_rounds = state.get(
            "max_clarification_rounds",
            self.max_clarification_rounds,
        )

        if (
            clarification_round
            >= max_rounds
        ):
            return "blocked"

        return "clarify"

    def _clarify_task(
        self,
        state: TaskIntakeState,
    ) -> dict:
        """
        Pause execution and request clarification from
        the user.

        IMPORTANT:
        No LLM call or non-idempotent side effect should
        occur before interrupt(), because LangGraph
        restarts this node when execution resumes.
        """

        task = state["task"]

        clarification_round = (
            state.get(
                "clarification_round",
                0,
            )
        )

        response = interrupt(
            {
                "type":
                    "task_clarification_required",

                "task_id":
                    task.id,

                "property_id":
                    task.property_id,

                "round":
                    clarification_round + 1,

                "ambiguities":
                    list(task.ambiguities),

                "allowed_actions": [
                    "clarify",
                    "assume_remaining",
                    "cancel",
                ],

                "instruction": (
                    "Please clarify the unresolved "
                    "requirements. You may also authorize "
                    "the system to make minimal assumptions "
                    "for any remaining task-level "
                    "ambiguities, or cancel the workflow."
                ),
            }
        )

        # Backward compatibility:
        # a plain string is treated as normal clarification.
        if isinstance(
            response,
            str,
        ):
            response = {
                "action": "clarify",
                "text": response,
            }

        try:
            clarification_response = (
                TaskClarificationResponse
                .model_validate(
                    response
                )
            )

        except Exception as exc:
            raise ValueError(
                "Invalid task clarification response."
            ) from exc

        return {
            "clarification_response":
                clarification_response
        }

    def _apply_clarification(
        self,
        state: TaskIntakeState,
    ) -> dict:

        scenario = state["scenario"]

        response = state[
            "clarification_response"
        ]

        clarification_round = (
            state.get(
                "clarification_round",
                0,
            )
            + 1
        )

        if (
            response.action
            == ClarificationAction.CANCEL
        ):
            return {
                "cancelled":
                    True,

                "clarification_round":
                    clarification_round,

                "clarification_response":
                    None,
            }

        clarifications = list(
            scenario.clarifications
        )

        if response.text:
            clarifications.append(
                response.text
            )

        updated_scenario = (
            scenario.model_copy(
                update={
                    "clarifications":
                        clarifications
                }
            )
        )

        return {
            "scenario":
                updated_scenario,

            "clarification_round":
                clarification_round,

            "clarification_response":
                None,

            "assume_remaining": (
                response.action
                == (
                    ClarificationAction
                    .ASSUME_REMAINING
                )
            ),

            "cancelled":
                False,
        }

    def _route_after_user_decision(
        self,
        state: TaskIntakeState,
    ) -> Literal[
        "reinterpret",
        "cancel",
    ]:

        if state.get(
            "cancelled",
            False,
        ):
            return "cancel"

        return "reinterpret"

    def _resolve_assumptions(
        self,
        state: TaskIntakeState,
    ) -> dict:

        if self.assumption_resolver is None:
            return {
                "terminal_reason":
                    "assumption_resolver_unavailable"
            }

        task = state["task"]

        resolved_task = (
            self.assumption_resolver.resolve(
                task
            )
        )

        return {
            "task":
                resolved_task,

            "assume_remaining":
                False,
        }

    def _route_after_assumptions(
        self,
        state: TaskIntakeState,
    ) -> Literal[
        "complete",
        "blocked",
    ]:

        task = state["task"]

        if not task.ambiguities:
            return "complete"

        return "blocked"

    def _finalize_cancelled(
        self,
        state: TaskIntakeState,
    ) -> dict:

        return {
            "complete":
                False,

            "terminal_reason":
                "clarification_cancelled",
        }

    def _finalize_complete(
        self,
        state: TaskIntakeState,
    ) -> dict:
        """
        Finalize a sufficiently specified task.
        """

        return {
            "complete": True,
            "terminal_reason":
                "task_ready",
        }

    def _finalize_blocked(
        self,
        state: TaskIntakeState,
    ) -> dict:
        """
        Stop when unresolved ambiguities remain after
        the configured clarification limit.
        """

        return {
            "complete": False,
            "terminal_reason":
                "clarification_limit_reached",
        }

    def start(
        self,
        scenario: NaturalLanguageScenario,
        thread_id: str,
    ):
        """
        Start a new task-intake workflow.
        """

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        return self.graph.invoke(
            {
                "scenario":
                    scenario,

                "clarification_round":
                    0,

                "max_clarification_rounds":
                    self.max_clarification_rounds,

                "assume_remaining":
                    False,

                "cancelled":
                    False,

                "complete":
                    False,

                "terminal_reason":
                    None,
            },
            config=config,
        )

    def resume(
        self,
        clarification,
        thread_id: str,
    ):
        """
        Resume a task waiting for user clarification.
        """

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        return self.graph.invoke(
            Command(
                resume=clarification
            ),
            config=config,
        )