from uuid import uuid4

from langgraph.checkpoint.memory import (
    InMemorySaver,
)

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from property_agent.agents import (
    PropertyGenerationError,
    PropertyRepairError,
    SemanticReviewError,
)

from property_agent.assessment import (
    build_final_assessment,
    save_final_assessment,
)

from property_agent.models import (
    CompilationStatus,
    FinalAssessmentStatus,
    PropertyGenerationResult,
    RepairDiagnosisStatus,
    RepairOutcomeStatus,
    RepairResult,
)

from property_agent.repair import (
    build_repair_diagnosis,
)

from property_agent.retrieval import (
    ExampleRetrievalError,
)

from property_agent.storage import (
    save_generated_property,
)

from .config import (
    PropertyWorkflowConfig,
)

from .dependencies import (
    WorkflowDependencies,
)

from .state import (
    PropertyWorkflowState,
)


class PropertyWorkflow:
    """
    LangGraph orchestration for autonomous MMT
    property generation.

    The graph coordinates existing deterministic tools
    and specialized LLM-backed agents.

    LangGraph itself does not perform semantic reasoning
    or property generation.
    """

    def __init__(
        self,
        dependencies: WorkflowDependencies,
        config: PropertyWorkflowConfig | None = None,
        checkpointer=None,
    ):
        self.dependencies = dependencies

        self.config = (
            config
            or PropertyWorkflowConfig()
        )

        self.checkpointer = (
            checkpointer
            or InMemorySaver()
        )

        self.graph = self._build_graph()

    # ======================================================
    # Graph construction
    # ======================================================

    def _build_graph(self):
        builder = StateGraph(
            PropertyWorkflowState
        )

        builder.add_node(
            "retrieve_examples",
            self._retrieve_examples,
        )

        builder.add_node(
            "generate",
            self._generate,
        )

        builder.add_node(
            "deterministic_validate",
            self._deterministic_validate,
        )

        builder.add_node(
            "semantic_review",
            self._semantic_review,
        )

        builder.add_node(
            "diagnose_repair",
            self._diagnose_repair,
        )

        builder.add_node(
            "repair",
            self._repair,
        )

        builder.add_node(
            "remote_compile",
            self._remote_compile,
        )

        builder.add_node(
            "finalize",
            self._finalize,
        )

        # --------------------------------------------------
        # Entry
        # --------------------------------------------------

        builder.add_edge(
            START,
            "retrieve_examples",
        )

        # --------------------------------------------------
        # Retrieval
        # --------------------------------------------------

        builder.add_conditional_edges(
            "retrieve_examples",
            self._route_after_retrieval,
            {
                "generate":
                    "generate",

                "finalize":
                    "finalize",
            },
        )

        # --------------------------------------------------
        # Generation
        # --------------------------------------------------

        builder.add_conditional_edges(
            "generate",
            self._route_after_generation,
            {
                "validate":
                    "deterministic_validate",

                "finalize":
                    "finalize",
            },
        )

        # --------------------------------------------------
        # Deterministic validation
        # --------------------------------------------------

        builder.add_conditional_edges(
            "deterministic_validate",
            self._route_after_validation,
            {
                "semantic":
                    "semantic_review",

                "diagnose":
                    "diagnose_repair",

                "finalize":
                    "finalize",
            },
        )

        # --------------------------------------------------
        # Semantic validation
        # --------------------------------------------------

        builder.add_conditional_edges(
            "semantic_review",
            self._route_after_semantic_review,
            {
                "compile":
                    "remote_compile",

                "diagnose":
                    "diagnose_repair",

                "finalize":
                    "finalize",
            },
        )

        # --------------------------------------------------
        # Repair diagnosis
        # --------------------------------------------------

        builder.add_conditional_edges(
            "diagnose_repair",
            self._route_after_diagnosis,
            {
                "repair":
                    "repair",

                "finalize":
                    "finalize",
            },
        )

        # --------------------------------------------------
        # Repair
        # --------------------------------------------------

        builder.add_conditional_edges(
            "repair",
            self._route_after_repair,
            {
                "validate":
                    "deterministic_validate",

                "finalize":
                    "finalize",
            },
        )

        # --------------------------------------------------
        # Compilation is terminal evidence
        # --------------------------------------------------

        builder.add_edge(
            "remote_compile",
            "finalize",
        )

        builder.add_edge(
            "finalize",
            END,
        )

        return builder.compile(
            checkpointer=self.checkpointer
        )

    # ======================================================
    # Nodes
    # ======================================================

    def _retrieve_examples(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Retrieve examples exactly once for the task.
        """

        try:
            retrieval_result = (
                self.dependencies
                .retriever
                .retrieve(
                    state["task"]
                )
            )

            return {
                "retrieval_result":
                    retrieval_result,

                "workflow_error":
                    None,
            }

        except ExampleRetrievalError as exc:
            return {
                "workflow_error":
                    str(exc),

                "terminal_reason":
                    "retrieval_error",
            }

    def _generate(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Generate the initial property candidate using
        the RetrievalResult already stored in graph state.
        """

        try:
            generated = (
                self.dependencies
                .generator
                .generate(
                    task=state["task"],
                    retrieval_result=(
                        state[
                            "retrieval_result"
                        ]
                    ),
                )
            )

            if self.config.save_artifacts:
                save_generated_property(
                    generated_property=generated,
                    output_root=(
                        self.config.results_dir
                    ),
                )

            return {
                "current_property":
                    generated,

                "property_history": [
                    generated
                ],

                "workflow_error":
                    None,

                "terminal_reason":
                    None,
            }

        except PropertyGenerationError as exc:
            return {
                "workflow_error":
                    str(exc),

                "terminal_reason":
                    "generation_error",
            }

    def _deterministic_validate(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Run deterministic validation in dependency order.

        XML
          ↓
        MMT syntax
          ↓
        MMT static

        Later validators are skipped when an earlier
        prerequisite fails.
        """

        current = state[
            "current_property"
        ]

        if current is None:
            return {
                "workflow_error":
                    (
                        "Deterministic validation "
                        "requested without a "
                        "current property."
                    ),

                "terminal_reason":
                    "workflow_state_error",
            }

        try:
            xml_result = (
                self.dependencies
                .xml_validator(
                    current.xml
                )
            )

            syntax_result = None
            static_result = None

            if xml_result.valid:
                syntax_result = (
                    self.dependencies
                    .syntax_validator(
                        current.xml
                    )
                )

            if (
                syntax_result is not None
                and syntax_result.valid
            ):
                static_result = (
                    self.dependencies
                    .static_validator(
                        current.xml
                    )
                )

            return {
                "xml_validation":
                    xml_result,

                "syntax_validation":
                    syntax_result,

                "static_validation":
                    static_result,

                # Any semantic result from an earlier
                # candidate must not survive repair.
                "semantic_report":
                    None,

                "repair_diagnosis":
                    None,

                "compilation_result":
                    None,

                "final_assessment":
                    None,

                "workflow_error":
                    None,
            }

        except Exception as exc:
            return {
                "workflow_error":
                    (
                        "Deterministic validation "
                        f"failed unexpectedly: {exc}"
                    ),

                "terminal_reason":
                    "validation_execution_error",
            }

    def _semantic_review(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Perform semantic review only after all local
        deterministic validation has succeeded.
        """

        current = state[
            "current_property"
        ]

        if current is None:
            return {
                "workflow_error":
                    (
                        "Semantic review requested "
                        "without a current property."
                    ),

                "terminal_reason":
                    "workflow_state_error",
            }

        try:
            report = (
                self.dependencies
                .semantic_reviewer
                .review(
                    task=state["task"],
                    generated_property=current,
                )
            )

            return {
                "semantic_report":
                    report,

                "repair_diagnosis":
                    None,

                "workflow_error":
                    None,
            }

        except SemanticReviewError as exc:
            return {
                "semantic_report":
                    None,

                "workflow_error":
                    str(exc),

                "terminal_reason":
                    "semantic_review_error",
            }

    def _diagnose_repair(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Deterministically decide whether the current
        failure can be repaired safely.
        """

        validation_results = [
            result
            for result in [
                state.get(
                    "xml_validation"
                ),
                state.get(
                    "syntax_validation"
                ),
                state.get(
                    "static_validation"
                ),
            ]
            if result is not None
        ]

        diagnosis = (
            build_repair_diagnosis(
                validation_results=(
                    validation_results
                ),
                semantic_report=(
                    state.get(
                        "semantic_report"
                    )
                ),
            )
        )

        updates = {
            "repair_diagnosis":
                diagnosis,

            "workflow_error":
                None,
        }

        if (
            diagnosis.status
            == RepairDiagnosisStatus.BLOCKED
        ):
            # No LLM repair is invoked, but we preserve
            # a RepairResult so FinalPropertyAssessment
            # can represent the blocked outcome.
            updates[
                "repair_result"
            ] = RepairResult(
                task_id=state["task"].id,
                status=(
                    RepairOutcomeStatus.BLOCKED
                ),
                diagnosis=diagnosis,
                repaired_property=None,
                metadata={
                    "blocked_by":
                        "repair_diagnosis"
                },
            )

            updates[
                "terminal_reason"
            ] = "repair_blocked"

        elif (
            diagnosis.status
            == RepairDiagnosisStatus.REPAIRABLE
            and state.get(
                "repair_count",
                0,
            )
            >= state.get(
                "max_repair_attempts",
                0,
            )
        ):
            updates[
                "terminal_reason"
            ] = "repair_limit_reached"

        elif (
            diagnosis.status
            == RepairDiagnosisStatus.NO_REPAIR_NEEDED
        ):
            updates[
                "terminal_reason"
            ] = "no_repair_action_available"

        else:
            updates[
                "terminal_reason"
            ] = None

        return updates

    def _repair(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Perform exactly one repair attempt.
        """

        current = state[
            "current_property"
        ]

        diagnosis = state[
            "repair_diagnosis"
        ]

        if (
            current is None
            or diagnosis is None
        ):
            return {
                "workflow_error":
                    (
                        "Repair requested without "
                        "a property or diagnosis."
                    ),

                "terminal_reason":
                    "workflow_state_error",
            }

        try:
            repair_result = (
                self.dependencies
                .repairer
                .repair(
                    task=state["task"],
                    current_property=current,
                    diagnosis=diagnosis,
                    semantic_report=(
                        state.get(
                            "semantic_report"
                        )
                    ),
                )
            )

        except PropertyRepairError as exc:
            return {
                "workflow_error":
                    str(exc),

                "terminal_reason":
                    "repair_execution_error",
            }

        if (
            repair_result.status
            != RepairOutcomeStatus.REPAIRED
            or repair_result.repaired_property
            is None
        ):
            return {
                "repair_result":
                    repair_result,

                "repair_history": [
                    repair_result
                ],

                "terminal_reason":
                    (
                        "repair_did_not_produce_"
                        "candidate"
                    ),
            }

        repaired = (
            repair_result
            .repaired_property
        )

        if self.config.save_artifacts:
            save_generated_property(
                generated_property=repaired,
                output_root=(
                    self.config.results_dir
                ),
            )

        return {
            "repair_result":
                repair_result,

            "repair_history": [
                repair_result
            ],

            "current_property":
                repaired,

            "property_history": [
                repaired
            ],

            "repair_count":
                state.get(
                    "repair_count",
                    0,
                )
                + 1,

            # New candidate means all previous
            # validation evidence is stale.
            "xml_validation":
                None,

            "syntax_validation":
                None,

            "static_validation":
                None,

            "semantic_report":
                None,

            "repair_diagnosis":
                None,

            "compilation_result":
                None,

            "final_assessment":
                None,

            "workflow_error":
                None,

            "terminal_reason":
                None,
        }

    def _remote_compile(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Perform the single final remote MMT compilation
        assessment.

        Compilation failure never enters the repair loop.
        """

        current = state[
            "current_property"
        ]

        if current is None:
            return {
                "workflow_error":
                    (
                        "Compilation requested "
                        "without a current property."
                    ),

                "terminal_reason":
                    "workflow_state_error",
            }

        try:
            result = (
                self.dependencies
                .compilation_client
                .compile_property(
                    current
                )
            )

        except Exception as exc:
            return {
                "workflow_error":
                    (
                        "Remote compilation client "
                        f"failed unexpectedly: {exc}"
                    ),

                "terminal_reason":
                    "compilation_client_error",
            }

        if (
            result.status
            == CompilationStatus.COMPILED
        ):
            terminal_reason = (
                "compiled"
            )

        elif (
            result.status
            == CompilationStatus.COMPILATION_FAILED
        ):
            terminal_reason = (
                "compilation_failed"
            )

        else:
            terminal_reason = (
                "compilation_inconclusive"
            )

        return {
            "compilation_result":
                result,

            "terminal_reason":
                terminal_reason,

            "workflow_error":
                None,
        }

    def _finalize(
        self,
        state: PropertyWorkflowState,
    ) -> dict:
        """
        Build the final deterministic result and persist
        the final research artifact when possible.
        """

        current = state.get(
            "current_property"
        )

        assessment = None

        if current is not None:
            assessment = (
                build_final_assessment(
                    generated_property=current,
                    property_id=(
                        state[
                            "task"
                        ].property_id
                    ),
                    xml_validation=(
                        state.get(
                            "xml_validation"
                        )
                    ),
                    syntax_validation=(
                        state.get(
                            "syntax_validation"
                        )
                    ),
                    static_validation=(
                        state.get(
                            "static_validation"
                        )
                    ),
                    semantic_report=(
                        state.get(
                            "semantic_report"
                        )
                    ),
                    compilation_result=(
                        state.get(
                            "compilation_result"
                        )
                    ),
                    repair_result=(
                        state.get(
                            "repair_result"
                        )
                    ),
                )
            )

            # FinalAssessment currently receives only the
            # latest RepairResult. Graph state knows the
            # complete number of repairs, so correct the
            # aggregate statistic here.
            assessment.statistics.repair_performed = (
                state.get(
                    "repair_count",
                    0,
                )
                > 0
            )

            if self.config.save_artifacts:
                save_final_assessment(
                    assessment=assessment,
                    generated_property=current,
                    output_root=(
                        self.config.results_dir
                    ),
                )

        success = (
            assessment is not None
            and assessment.status
            == FinalAssessmentStatus.ACCEPTED
        )

        retrieval = state.get(
            "retrieval_result"
        )

        result = PropertyGenerationResult(
            task_id=state["task"].id,
            success=success,
            property=current,
            xml_validation=(
                state.get(
                    "xml_validation"
                )
            ),
            syntax_validation=(
                state.get(
                    "syntax_validation"
                )
            ),
            static_validation=(
                state.get(
                    "static_validation"
                )
            ),
            semantic_validation=(
                state.get(
                    "semantic_report"
                )
            ),
            repair_result=(
                state.get(
                    "repair_result"
                )
            ),
            compilation_validation=(
                state.get(
                    "compilation_result"
                )
            ),
            final_assessment=assessment,
            attempts=(
                current.attempt
                if current is not None
                else 0
            ),
            metadata={
                "workflow": {
                    "terminal_reason":
                        state.get(
                            "terminal_reason"
                        ),

                    "workflow_error":
                        state.get(
                            "workflow_error"
                        ),

                    "repair_count":
                        state.get(
                            "repair_count",
                            0,
                        ),

                    "max_repair_attempts":
                        state.get(
                            "max_repair_attempts",
                            0,
                        ),

                    "retrieval_enabled":
                        (
                            retrieval.enabled
                            if retrieval
                            is not None
                            else None
                        ),

                    "retrieved_example_ids":
                        (
                            [
                                example.property_id
                                for example
                                in retrieval.examples
                            ]
                            if retrieval
                            is not None
                            else []
                        ),
                }
            },
        )

        return {
            "final_assessment":
                assessment,

            "result":
                result,
        }

    # ======================================================
    # Routing
    # ======================================================

    @staticmethod
    def _route_after_retrieval(
        state: PropertyWorkflowState,
    ) -> str:

        if state.get(
            "workflow_error"
        ):
            return "finalize"

        return "generate"

    @staticmethod
    def _route_after_generation(
        state: PropertyWorkflowState,
    ) -> str:

        if (
            state.get(
                "workflow_error"
            )
            or state.get(
                "current_property"
            )
            is None
        ):
            return "finalize"

        return "validate"

    @staticmethod
    def _route_after_validation(
        state: PropertyWorkflowState,
    ) -> str:

        if state.get(
            "workflow_error"
        ):
            return "finalize"

        xml_result = state.get(
            "xml_validation"
        )

        syntax_result = state.get(
            "syntax_validation"
        )

        static_result = state.get(
            "static_validation"
        )

        local_valid = (
            xml_result is not None
            and xml_result.valid
            and syntax_result is not None
            and syntax_result.valid
            and static_result is not None
            and static_result.valid
        )

        if local_valid:
            return "semantic"

        return "diagnose"

    @staticmethod
    def _route_after_semantic_review(
        state: PropertyWorkflowState,
    ) -> str:

        if state.get(
            "workflow_error"
        ):
            return "finalize"

        report = state.get(
            "semantic_report"
        )

        if report is None:
            return "finalize"

        if report.valid:
            return "compile"

        return "diagnose"

    @staticmethod
    def _route_after_diagnosis(
        state: PropertyWorkflowState,
    ) -> str:

        diagnosis = state.get(
            "repair_diagnosis"
        )

        if diagnosis is None:
            return "finalize"

        if (
            diagnosis.status
            != RepairDiagnosisStatus.REPAIRABLE
        ):
            return "finalize"

        if (
            state.get(
                "repair_count",
                0,
            )
            >= state.get(
                "max_repair_attempts",
                0,
            )
        ):
            return "finalize"

        return "repair"

    @staticmethod
    def _route_after_repair(
        state: PropertyWorkflowState,
    ) -> str:

        if state.get(
            "workflow_error"
        ):
            return "finalize"

        repair_result = state.get(
            "repair_result"
        )

        if (
            repair_result is not None
            and repair_result.status
            == RepairOutcomeStatus.REPAIRED
            and state.get(
                "current_property"
            )
            is not None
        ):
            return "validate"

        return "finalize"

    # ======================================================
    # Public execution API
    # ======================================================

    def invoke(
        self,
        task,
        thread_id: str | None = None,
    ) -> PropertyWorkflowState:
        """
        Execute the workflow and return complete graph
        state.

        Useful for debugging and experiments.
        """

        resolved_thread_id = (
            thread_id
            or (
                f"{task.id}-"
                f"{uuid4().hex}"
            )
        )

        initial_state = {
            "task":
                task,

            "retrieval_result":
                None,

            "current_property":
                None,

            "property_history":
                [],

            "xml_validation":
                None,

            "syntax_validation":
                None,

            "static_validation":
                None,

            "semantic_report":
                None,

            "repair_diagnosis":
                None,

            "repair_result":
                None,

            "repair_history":
                [],

            "compilation_result":
                None,

            "final_assessment":
                None,

            "result":
                None,

            "repair_count":
                0,

            "max_repair_attempts":
                self.config
                .max_repair_attempts,

            "terminal_reason":
                None,

            "workflow_error":
                None,
        }

        return self.graph.invoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id":
                        resolved_thread_id,
                },
                "recursion_limit":
                    self.config
                    .recursion_limit,
            },
        )

    def run(
        self,
        task,
        thread_id: str | None = None,
    ) -> PropertyGenerationResult:
        """
        Execute one monitoring task and return only the
        final public pipeline result.
        """

        state = self.invoke(
            task=task,
            thread_id=thread_id,
        )

        result = state.get(
            "result"
        )

        if result is None:
            raise RuntimeError(
                "Workflow terminated without "
                "producing a "
                "PropertyGenerationResult."
            )

        return result