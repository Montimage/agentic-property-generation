import argparse
import json
from pathlib import Path

from property_agent.agents import (
    PropertyGenerator,
)

from property_agent.llm import (
    LLMClient,
    LLMConfig,
)

from property_agent.models import (
    MonitoringTask,
    RetrievalConfig,
)

from property_agent.retrieval import (
    VerifiedExampleRetriever,
)

from property_agent.storage import (
    save_generated_property,
)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate an MMT monitoring property."
        )
    )

    parser.add_argument(
        "scenario",
        help="Path to a MonitoringTask JSON file.",
    )

    parser.add_argument(
        "--model",
        required=True,
        help=(
            "LiteLLM model identifier, "
            "e.g. ollama/qwen2.5-coder:7b"
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

    parser.add_argument(
        "--retrieval",
        action="store_true",
        help=(
            "Enable retrieval of curated "
            "verified property examples."
        ),
    )

    parser.add_argument(
        "--retrieval-k",
        type=int,
        default=2,
        help=(
            "Maximum number of verified "
            "examples to retrieve."
        ),
    )

    parser.add_argument(
        "--retrieval-min-score",
        type=float,
        default=0.55,
        help=(
            "Minimum deterministic relevance "
            "score required for retrieval."
        ),
    )

    parser.add_argument(
        "--save-results",
        action="store_true",
        help=(
            "Persist the generated candidate "
            "for later evaluation."
        ),
    )

    parser.add_argument(
        "--results-dir",
        default="results",
        help=(
            "Directory used for generated "
            "experimental artifacts."
        ),
    )

    args = parser.parse_args()

    scenario_path = Path(
        args.scenario
    )

    data = json.loads(
        scenario_path.read_text(
            encoding="utf-8"
        )
    )

    task = MonitoringTask.model_validate(
        data
    )

    config = LLMConfig(
        model=args.model,
        api_base=args.api_base,
        temperature=args.temperature,
    )

    client = LLMClient(config)

    retriever = VerifiedExampleRetriever(
        config=RetrievalConfig(
            enabled=args.retrieval,
            k=args.retrieval_k,
            min_score=(
                args.retrieval_min_score
            ),
        )
    )

    generator = PropertyGenerator(
        client=client,
        example_retriever=retriever,
    )

    result = generator.generate(task)

    print(result.xml)

    if args.save_results:
        save_generated_property(
            generated_property=result,
            output_root=args.results_dir,
        )


if __name__ == "__main__":
    main()