from dataclasses import dataclass

from property_agent.agents import (
    PropertyGenerator,
    PropertyRepairer,
    SemanticReviewer,
    TaskAssumptionResolver,
    TaskInterpreter,
)

from property_agent.llm import (
    LLMClient,
    LLMConfig,
)

from property_agent.models import (
    RetrievalConfig,
)

from property_agent.retrieval import (
    VerifiedExampleRetriever,
)

from property_agent.tools import (
    MMTCompilationClient,
    MMTCompilationConfig,
)

from property_agent.tools.mmt_static_validator import (
    validate_mmt_static,
)

from property_agent.tools.mmt_syntax_validator import (
    validate_mmt_syntax,
)

from property_agent.tools.xml_validator import (
    validate_xml,
)

from .config import (
    PropertyWorkflowConfig,
)

from .dependencies import (
    WorkflowDependencies,
)

from .graph import (
    PropertyWorkflow,
)

from .intake_graph import (
    TaskIntakeWorkflow,
)

from .natural_language import (
    NaturalLanguagePropertyWorkflow,
)


@dataclass
class PropertyWorkflowRuntime:
    """
    Concrete runtime environment for the complete
    property-generation workflow.
    """

    workflow: PropertyWorkflow

    llm_client: LLMClient

    retriever: VerifiedExampleRetriever

    compilation_client: MMTCompilationClient


@dataclass
class NaturalLanguageWorkflowRuntime:
    """
    Concrete runtime for the complete natural-language
    monitoring-property workflow.

    The runtime combines:

    - natural-language task interpretation;
    - user clarification;
    - authorized assumption resolution;
    - the existing property workflow.

    All LLM-backed agents share the same LLMClient so
    model configuration remains controlled and
    reproducible.
    """

    workflow: NaturalLanguagePropertyWorkflow

    intake_workflow: TaskIntakeWorkflow

    property_runtime: PropertyWorkflowRuntime

    task_interpreter: TaskInterpreter

    assumption_resolver: TaskAssumptionResolver

    llm_client: LLMClient

    retriever: VerifiedExampleRetriever

    compilation_client: MMTCompilationClient


def build_property_workflow(
    *,
    model: str,
    mmt_endpoint: str,
    api_base: str | None = None,
    temperature: float = 0.0,
    llm_timeout: float | None = 300.0,
    retrieval_enabled: bool = False,
    retrieval_k: int = 2,
    retrieval_min_score: float = 0.55,
    max_repair_attempts: int = 2,
    save_artifacts: bool = True,
    results_dir: str = "results",
    checkpointer=None,
) -> PropertyWorkflowRuntime:
    """
    Build the real property-generation runtime.

    All LLM-backed agents share the same provider-neutral
    LLMClient.

    Retrieval is executed exactly once per task by the
    LangGraph workflow.

    Remote MMT compilation is final validation evidence.
    """

    # --------------------------------------------------
    # Shared LLM
    # --------------------------------------------------

    llm_config = LLMConfig(
        model=model,
        api_base=api_base,
        temperature=temperature,
        timeout=llm_timeout,
    )

    llm_client = LLMClient(
        llm_config
    )

    # --------------------------------------------------
    # Verified-example retrieval
    # --------------------------------------------------

    retriever = VerifiedExampleRetriever(
        config=RetrievalConfig(
            enabled=retrieval_enabled,
            k=retrieval_k,
            min_score=retrieval_min_score,
        )
    )

    # --------------------------------------------------
    # LLM-backed specialized agents
    # --------------------------------------------------

    generator = PropertyGenerator(
        client=llm_client,
        example_retriever=retriever,
    )

    semantic_reviewer = SemanticReviewer(
        client=llm_client,
    )

    repairer = PropertyRepairer(
        client=llm_client,
    )

    # --------------------------------------------------
    # Real MMT compilation client
    # --------------------------------------------------

    compilation_client = (
        MMTCompilationClient(
            config=MMTCompilationConfig(
                base_url=mmt_endpoint,
            )
        )
    )

    # --------------------------------------------------
    # Workflow dependencies
    # --------------------------------------------------

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=semantic_reviewer,
        repairer=repairer,
        retriever=retriever,
        compilation_client=(
            compilation_client
        ),
        xml_validator=validate_xml,
        syntax_validator=(
            validate_mmt_syntax
        ),
        static_validator=(
            validate_mmt_static
        ),
    )

    # --------------------------------------------------
    # LangGraph workflow
    # --------------------------------------------------

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=(
                max_repair_attempts
            ),
            save_artifacts=save_artifacts,
            results_dir=results_dir,
        ),
        checkpointer=checkpointer,
    )

    return PropertyWorkflowRuntime(
        workflow=workflow,
        llm_client=llm_client,
        retriever=retriever,
        compilation_client=(
            compilation_client
        ),
    )


def build_natural_language_workflow(
    *,
    model: str,
    mmt_endpoint: str,
    api_base: str | None = None,
    temperature: float = 0.0,
    llm_timeout: float | None = 300.0,
    retrieval_enabled: bool = False,
    retrieval_k: int = 2,
    retrieval_min_score: float = 0.55,
    max_repair_attempts: int = 2,
    max_clarification_rounds: int = 3,
    save_artifacts: bool = True,
    results_dir: str = "results",
    property_checkpointer=None,
    intake_checkpointer=None,
) -> NaturalLanguageWorkflowRuntime:
    """
    Build the complete natural-language runtime.

    The existing runtime is constructed first.
    Its LLMClient is then reused by the TaskInterpreter
    and TaskAssumptionResolver.

    Intake workflows remain independent.
    """

    # --------------------------------------------------
    # Existing runtime
    # --------------------------------------------------

    property_runtime = (
        build_property_workflow(
            model=model,
            mmt_endpoint=mmt_endpoint,
            api_base=api_base,
            temperature=temperature,
            llm_timeout=llm_timeout,
            retrieval_enabled=(
                retrieval_enabled
            ),
            retrieval_k=retrieval_k,
            retrieval_min_score=(
                retrieval_min_score
            ),
            max_repair_attempts=(
                max_repair_attempts
            ),
            save_artifacts=(
                save_artifacts
            ),
            results_dir=results_dir,
            checkpointer=(
                property_checkpointer
            ),
        )
    )

    # Reuse exactly the same LLM configuration.
    llm_client = (
        property_runtime.llm_client
    )

    # --------------------------------------------------
    # Natural-language intake agents
    # --------------------------------------------------

    task_interpreter = TaskInterpreter(
        client=llm_client,
    )

    assumption_resolver = (
        TaskAssumptionResolver(
            client=llm_client,
        )
    )

    # --------------------------------------------------
    # Intake / clarification workflow
    # --------------------------------------------------

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                task_interpreter
            ),
            assumption_resolver=(
                assumption_resolver
            ),
            max_clarification_rounds=(
                max_clarification_rounds
            ),
            checkpointer=(
                intake_checkpointer
            ),
        )
    )

    # --------------------------------------------------
    # Natural-language integration facade
    # --------------------------------------------------

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_runtime.workflow
            ),
        )
    )

    return NaturalLanguageWorkflowRuntime(
        workflow=workflow,
        intake_workflow=(
            intake_workflow
        ),
        property_runtime=(
            property_runtime
        ),
        task_interpreter=(
            task_interpreter
        ),
        assumption_resolver=(
            assumption_resolver
        ),
        llm_client=llm_client,
        retriever=(
            property_runtime.retriever
        ),
        compilation_client=(
            property_runtime
            .compilation_client
        ),
    )