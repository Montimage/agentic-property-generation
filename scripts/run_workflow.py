import argparse
import json
from pathlib import Path

from property_agent.models import (
    MonitoringTask,
)

from property_agent.workflow import (
    build_property_workflow,
)


def _validation_summary(
    result,
):
    if result is None:
        return None

    return {
        "validator":
            result.validator,

        "valid":
            result.valid,

        "issue_count":
            len(result.issues),

        "issues": [
            {
                "code":
                    issue.code,

                "severity":
                    issue.severity.value,

                "message":
                    issue.message,
            }
            for issue in result.issues
        ],
    }


def _build_summary(
    *,
    state,
):
    """
    Build a compact human-readable execution summary
    without printing the complete LangGraph state.
    """

    result = state.get(
        "result"
    )

    retrieval = state.get(
        "retrieval_result"
    )

    compilation = state.get(
        "compilation_result"
    )

    assessment = state.get(
        "final_assessment"
    )

    semantic = state.get(
        "semantic_report"
    )

    current_property = state.get(
        "current_property"
    )

    return {
        "task_id": (
            result.task_id
            if result is not None
            else state["task"].id
        ),

        "property_id":
            state["task"].property_id,

        "success": (
            result.success
            if result is not None
            else False
        ),

        "terminal_reason":
            state.get(
                "terminal_reason"
            ),

        "workflow_error":
            state.get(
                "workflow_error"
            ),

        "final_attempt": (
            current_property.attempt
            if current_property
            is not None
            else None
        ),

        "repair_count":
            state.get(
                "repair_count",
                0,
            ),

        "property_history_attempts": [
            item.attempt
            for item
            in state.get(
                "property_history",
                [],
            )
        ],

        "retrieval": (
            {
                "enabled":
                    retrieval.enabled,

                "requested_k":
                    retrieval.requested_k,

                "candidate_count":
                    retrieval.candidate_count,

                "selected_examples": [
                    {
                        "property_id":
                            example.property_id,

                        "score":
                            example.score,
                    }
                    for example
                    in retrieval.examples
                ],
            }
            if retrieval is not None
            else None
        ),

        "deterministic_validation": {
            "xml":
                _validation_summary(
                    state.get(
                        "xml_validation"
                    )
                ),

            "syntax":
                _validation_summary(
                    state.get(
                        "syntax_validation"
                    )
                ),

            "static":
                _validation_summary(
                    state.get(
                        "static_validation"
                    )
                ),
        },

        "semantic_validation": (
            {
                "valid":
                    semantic.valid,

                "overall_score":
                    semantic.overall_score,

                "summary":
                    semantic.summary,

                "dimensions": {
                    "message_exchange_semantics": {
                        "score": (
                            semantic
                            .message_exchange_semantics
                            .score
                        ),
                        "justification": (
                            semantic
                            .message_exchange_semantics
                            .justification
                        ),
                        "issues": [
                            {
                                "type":
                                    issue.type.value,
                                "message":
                                    issue.message,
                                "evidence":
                                    issue.evidence,
                            }
                            for issue
                            in semantic
                            .message_exchange_semantics
                            .issues
                        ],
                    },

                    "temporal_ordering_semantics": {
                        "score": (
                            semantic
                            .temporal_ordering_semantics
                            .score
                        ),
                        "justification": (
                            semantic
                            .temporal_ordering_semantics
                            .justification
                        ),
                        "issues": [
                            {
                                "type":
                                    issue.type.value,
                                "message":
                                    issue.message,
                                "evidence":
                                    issue.evidence,
                            }
                            for issue
                            in semantic
                            .temporal_ordering_semantics
                            .issues
                        ],
                    },

                    "detection_semantics": {
                        "score": (
                            semantic
                            .detection_semantics
                            .score
                        ),
                        "justification": (
                            semantic
                            .detection_semantics
                            .justification
                        ),
                        "issues": [
                            {
                                "type":
                                    issue.type.value,
                                "message":
                                    issue.message,
                                "evidence":
                                    issue.evidence,
                            }
                            for issue
                            in semantic
                            .detection_semantics
                            .issues
                        ],
                    },

                    "attribute_relevance": {
                        "score": (
                            semantic
                            .attribute_relevance
                            .score
                        ),
                        "justification": (
                            semantic
                            .attribute_relevance
                            .justification
                        ),
                        "issues": [
                            {
                                "type":
                                    issue.type.value,
                                "message":
                                    issue.message,
                                "evidence":
                                    issue.evidence,
                            }
                            for issue
                            in semantic
                            .attribute_relevance
                            .issues
                        ],
                    },
                },

                "recommendations":
                    semantic.recommendations,
            }
            if semantic is not None
            else None
        ),

        "compilation": (
            {
                "status":
                    compilation.status.value,

                "compile_ok":
                    compilation.compile_ok,

                "returncode":
                    compilation.returncode,

                "http_status":
                    compilation.http_status,

                "message":
                    compilation.message,

                "stdout":
                    compilation.stdout,

                "stderr":
                    compilation.stderr,

                "remote_duration_ms":
                    compilation.remote_duration_ms,

                "client_duration_ms":
                    compilation.client_duration_ms,

                "local_xml_sha256":
                    compilation.local_xml_sha256,

                "remote_xml_sha256":
                    compilation.remote_xml_sha256,

                "hash_matches":
                    compilation.hash_matches,

                "compiled_artifact_created":
                    compilation.compiled_artifact_created,

                "cleanup_enabled":
                    compilation.cleanup_enabled,

                "artifacts_deleted":
                    compilation.artifacts_deleted,

                "cleanup_errors":
                    compilation.cleanup_errors,
            }
            if compilation is not None
            else None
        ),

        "final_assessment": (
            {
                "status":
                    assessment.status.value,

                "semantic_score":
                    assessment.semantic_score,

                "reasons":
                    assessment.reasons,

                "statistics":
                    assessment.statistics
                    .model_dump(
                        mode="json"
                    ),
            }
            if assessment is not None
            else None
        ),
    }


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run the complete agentic MMT "
            "property-generation workflow."
        )
    )

    # --------------------------------------------------
    # Task
    # --------------------------------------------------

    parser.add_argument(
        "scenario",
        type=Path,
        help=(
            "Path to a MonitoringTask JSON file."
        ),
    )

    # --------------------------------------------------
    # LLM
    # --------------------------------------------------

    parser.add_argument(
        "--model",
        required=True,
        help=(
            "LiteLLM model identifier, e.g. "
            "ollama/qwen2.5-coder:7b"
        ),
    )

    parser.add_argument(
        "--api-base",
        default=None,
        help=(
            "Optional provider API base. "
            "For local Ollama: "
            "http://localhost:11434"
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
    )

    # --------------------------------------------------
    # Remote MMT compiler
    # --------------------------------------------------

    parser.add_argument(
        "--mmt-endpoint",
        required=True,
        help=(
            "Base URL of the remote MMT "
            "compilation receiver."
        ),
    )

    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help=(
            "Skip the remote MMT endpoint "
            "health check before execution."
        ),
    )

    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    parser.add_argument(
        "--retrieval",
        action="store_true",
        help=(
            "Enable retrieval of curated "
            "validated property examples."
        ),
    )

    parser.add_argument(
        "--retrieval-k",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--retrieval-min-score",
        type=float,
        default=0.55,
    )

    # --------------------------------------------------
    # Repair
    # --------------------------------------------------

    parser.add_argument(
        "--max-repair-attempts",
        type=int,
        default=2,
        help=(
            "Maximum number of autonomous "
            "repair attempts."
        ),
    )

    # --------------------------------------------------
    # Artifacts
    # --------------------------------------------------

    parser.add_argument(
        "--results-dir",
        default="results",
    )

    parser.add_argument(
        "--no-save-results",
        action="store_true",
        help=(
            "Do not persist generated "
            "workflow artifacts."
        ),
    )

    # --------------------------------------------------
    # LangGraph
    # --------------------------------------------------

    parser.add_argument(
        "--thread-id",
        default=None,
        help=(
            "Optional LangGraph thread identifier."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional path for saving the "
            "execution summary as JSON."
        ),
    )

    args = parser.parse_args()

    # --------------------------------------------------
    # Load task
    # --------------------------------------------------

    data = json.loads(
        args.scenario.read_text(
            encoding="utf-8"
        )
    )

    task = MonitoringTask.model_validate(
        data
    )

    # --------------------------------------------------
    # Build runtime
    # --------------------------------------------------

    runtime = build_property_workflow(
        model=args.model,
        api_base=args.api_base,
        temperature=args.temperature,
        mmt_endpoint=args.mmt_endpoint,
        retrieval_enabled=(
            args.retrieval
        ),
        retrieval_k=(
            args.retrieval_k
        ),
        retrieval_min_score=(
            args.retrieval_min_score
        ),
        max_repair_attempts=(
            args.max_repair_attempts
        ),
        save_artifacts=(
            not args.no_save_results
        ),
        results_dir=(
            args.results_dir
        ),
    )

    # --------------------------------------------------
    # Verify real MMT endpoint
    # --------------------------------------------------

    if not args.skip_health_check:

        print(
            "Checking remote MMT "
            "compilation endpoint..."
        )

        health = (
            runtime
            .compilation_client
            .check_health()
        )

        print(
            json.dumps(
                health,
                indent=2,
            )
        )

        if not health.get(
            "ok",
            False,
        ):
            raise SystemExit(
                "Remote MMT compilation "
                "endpoint is not healthy."
            )

        print()

    # --------------------------------------------------
    # Execute LangGraph
    # --------------------------------------------------

    print(
        "Running property-generation workflow..."
    )

    state = runtime.workflow.invoke(
        task=task,
        thread_id=args.thread_id,
    )

    summary = _build_summary(
        state=state
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print()
    print(
        "Workflow result:"
    )

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    current_property = state.get(
        "current_property"
    )

    if current_property is not None:

        print()
        print(
            "Final property:"
        )

        print()
        print(
            current_property.xml
        )

    if args.output is not None:

        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(
            json.dumps(
                summary,
                indent=2,
            ),
            encoding="utf-8",
        )

        print()
        print(
            "Execution summary saved to:"
        )

        print(
            args.output
        )


if __name__ == "__main__":
    main()