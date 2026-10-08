from property_agent.workflow import (
    build_natural_language_workflow,
)


def test_natural_language_runtime_wiring():
    runtime = (
        build_natural_language_workflow(
            model=(
                "fake/runtime-model"
            ),
            api_base=(
                "http://localhost:11434"
            ),
            mmt_endpoint=(
                "http://localhost:8000"
            ),
            retrieval_enabled=False,
            save_artifacts=False,
        )
    )

    # Integration facade uses the exact intake
    # workflow constructed by the runtime.
    assert (
        runtime.workflow
        .intake_workflow
        is runtime.intake_workflow
    )

    # Integration facade uses the existing Stage 9
    # workflow.
    assert (
        runtime.workflow
        .property_workflow
        is runtime
        .property_runtime
        .workflow
    )

    # Intake agents reuse the Stage 9 LLM client.
    assert (
        runtime
        .task_interpreter
        .client
        is runtime.llm_client
    )

    assert (
        runtime
        .assumption_resolver
        .client
        is runtime.llm_client
    )

    assert (
        runtime
        .property_runtime
        .llm_client
        is runtime.llm_client
    )

    # Stage 9 components are also exposed through the
    # complete runtime.
    assert (
        runtime.retriever
        is runtime
        .property_runtime
        .retriever
    )

    assert (
        runtime.compilation_client
        is runtime
        .property_runtime
        .compilation_client
    )