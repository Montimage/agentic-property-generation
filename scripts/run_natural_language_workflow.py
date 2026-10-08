import argparse
import json
from pathlib import Path
from uuid import uuid4

from property_agent.models import (
    NaturalLanguageScenario,
    NaturalLanguageWorkflowStatus,
)

from property_agent.workflow import (
    build_natural_language_workflow,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete natural-language "
            "MMT property-generation workflow."
        )
    )

    parser.add_argument(
        "--task-id",
        required=True,
    )

    parser.add_argument(
        "--property-id",
        required=True,
    )

    parser.add_argument(
        "--scenario",
        required=True,
        help=(
            "Natural-language monitoring scenario."
        ),
    )

    parser.add_argument(
        "--model",
        required=True,
    )

    parser.add_argument(
        "--api-base",
        default=None,
    )

    parser.add_argument(
        "--mmt-endpoint",
        required=True,
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
    )

    parser.add_argument(
        "--retrieval",
        action="store_true",
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

    parser.add_argument(
        "--max-repair-attempts",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--max-clarification-rounds",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--results-dir",
        default="results",
    )

    parser.add_argument(
        "--no-save-artifacts",
        action="store_true",
    )

    parser.add_argument(
        "--thread-id",
        default=None,
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional JSON file for the final "
            "natural-language workflow result."
        ),
    )

    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=300.0,
        help=(
            "Maximum time in seconds for each "
            "LLM request. Default: 300."
        ),
    )

    return parser


def print_clarification_request(
    result,
) -> None:
    payload = (
        result.clarification_payload
        or {}
    )

    ambiguities = payload.get(
        "ambiguities",
        [],
    )

    round_number = payload.get(
        "round",
        "?",
    )

    print()
    print("=" * 72)
    print(
        f"USER CLARIFICATION REQUIRED "
        f"(round {round_number})"
    )
    print("=" * 72)

    if ambiguities:
        print()
        print(
            "The monitoring task still contains "
            "the following ambiguities:"
        )
        print()

        for index, ambiguity in enumerate(
            ambiguities,
            start=1,
        ):
            print(
                f"  {index}. {ambiguity}"
            )

    print()
    print(
        "Choose one action:"
    )
    print(
        "  [c] Clarify the missing information"
    )
    print(
        "  [a] Authorize minimal assumptions "
        "for what remains"
    )
    print(
        "  [x] Cancel the workflow"
    )
    print()


def ask_user_for_decision() -> dict:
    while True:
        choice = input(
            "Action [c/a/x]: "
        ).strip().lower()

        if choice in {
            "c",
            "clarify",
        }:
            while True:
                text = input(
                    "Clarification: "
                ).strip()

                if text:
                    return {
                        "action":
                            "clarify",

                        "text":
                            text,
                    }

                print(
                    "Clarification text cannot "
                    "be empty."
                )

        if choice in {
            "a",
            "assume",
            "assume_remaining",
        }:
            text = input(
                "Optional clarification before "
                "assumptions "
                "(press Enter to skip): "
            ).strip()

            return {
                "action":
                    "assume_remaining",

                "text":
                    text or None,
            }

        if choice in {
            "x",
            "cancel",
        }:
            return {
                "action":
                    "cancel",
            }

        print(
            "Invalid action. Choose c, a, or x."
        )


def print_task(
    task,
) -> None:
    print()
    print("=" * 72)
    print("FINAL MONITORING TASK")
    print("=" * 72)

    print(
        json.dumps(
            task.model_dump(
                mode="json"
            ),
            indent=2,
        )
    )


def print_final_result(
    result,
) -> None:
    print()
    print("=" * 72)
    print("WORKFLOW RESULT")
    print("=" * 72)

    print(
        f"Status: {result.status.value}"
    )

    if result.task is not None:
        print(
            f"Task ID: {result.task.id}"
        )

        print(
            "Property ID: "
            f"{result.task.property_id}"
        )

        clarification_count = (
            result.metadata.get(
                "clarification_count",
                0,
            )
        )

        assumption_count = len(
            result.task.assumptions
        )

        print(
            "Clarifications: "
            f"{clarification_count}"
        )

        print(
            "Authorized assumptions: "
            f"{assumption_count}"
        )

    property_result = (
        result.property_result
    )

    if property_result is None:
        terminal_reason = (
            result.metadata.get(
                "terminal_reason"
            )
        )

        if terminal_reason:
            print(
                "Terminal reason: "
                f"{terminal_reason}"
            )

        return

    print(
        "Property workflow success: "
        f"{property_result.success}"
    )

    print(
        "Property attempts: "
        f"{property_result.attempts}"
    )

    if (
        property_result.final_assessment
        is not None
    ):
        assessment_status = (
            property_result
            .final_assessment
            .status
            .value
        )

        print(
            "Final assessment: "
            f"{assessment_status}"
        )

    if (
        property_result.compilation_validation
        is not None
    ):
        compilation_status = (
            property_result
            .compilation_validation
            .status
            .value
        )

        print(
            "Compilation status: "
            f"{compilation_status}"
        )


def save_result(
    result,
    output_path: str,
) -> None:
    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            result.model_dump(
                mode="json"
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"Result saved to: {path}"
    )


def main() -> None:
    args = (
        build_parser()
        .parse_args()
    )

    runtime = (
        build_natural_language_workflow(
            model=args.model,
            api_base=args.api_base,
            mmt_endpoint=(
                args.mmt_endpoint
            ),
            temperature=(
                args.temperature
            ),
            llm_timeout=(
                args.llm_timeout
            ),
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
            max_clarification_rounds=(
                args
                .max_clarification_rounds
            ),
            save_artifacts=(
                not args
                .no_save_artifacts
            ),
            results_dir=(
                args.results_dir
            ),
        )
    )

    scenario = (
        NaturalLanguageScenario(
            id=args.task_id,
            property_id=(
                args.property_id
            ),
            text=args.scenario,
            metadata={
                "runner":
                    (
                        "run_natural_language_"
                        "workflow"
                    ),
            },
        )
    )

    thread_id = (
        args.thread_id
        or (
            f"{args.task_id}-"
            f"{uuid4().hex}"
        )
    )

    print()
    print("=" * 72)
    print(
        "NATURAL-LANGUAGE PROPERTY WORKFLOW"
    )
    print("=" * 72)

    print(
        f"Thread ID: {thread_id}"
    )

    print()
    print(
        f"Scenario: {scenario.text}"
    )

    result = (
        runtime.workflow.start(
            scenario=scenario,
            thread_id=thread_id,
        )
    )

    while (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .CLARIFICATION_REQUIRED
        )
    ):
        print_clarification_request(
            result
        )

        decision = (
            ask_user_for_decision()
        )

        result = (
            runtime.workflow.resume(
                clarification=decision,
                thread_id=thread_id,
            )
        )

    if result.task is not None:
        print_task(
            result.task
        )

    print_final_result(
        result
    )

    if args.output:
        save_result(
            result=result,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()