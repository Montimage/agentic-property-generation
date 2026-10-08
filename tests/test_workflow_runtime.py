from property_agent.workflow import (
    PropertyWorkflow,
    PropertyWorkflowRuntime,
    build_property_workflow,
)


def test_build_property_workflow_runtime():
    runtime = build_property_workflow(
        model="ollama/test-model",
        api_base=(
            "http://localhost:11434"
        ),
        mmt_endpoint=(
            "http://localhost:8000"
        ),
        retrieval_enabled=True,
        retrieval_k=2,
        retrieval_min_score=0.55,
        max_repair_attempts=2,
        save_artifacts=False,
    )

    assert isinstance(
        runtime,
        PropertyWorkflowRuntime,
    )

    assert isinstance(
        runtime.workflow,
        PropertyWorkflow,
    )

    assert (
        runtime
        .retriever
        .config
        .enabled
        is True
    )

    assert (
        runtime
        .retriever
        .config
        .k
        == 2
    )

    assert (
        runtime
        .retriever
        .config
        .min_score
        == 0.55
    )

    assert (
        runtime
        .workflow
        .config
        .max_repair_attempts
        == 2
    )

    assert (
        runtime
        .workflow
        .config
        .save_artifacts
        is False
    )