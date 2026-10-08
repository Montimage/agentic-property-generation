import hashlib
import json
import re
from collections.abc import Callable

from pydantic import ValidationError

from property_agent.knowledge import (
    load_example_index,
    load_property_example,
)

from property_agent.models import (
    MonitoringTask,
    RetrievalConfig,
    RetrievalResult,
    RetrievedExample,
    VerifiedExampleMetadata,
)


class ExampleRetrievalError(RuntimeError):
    """
    Raised when the curated example repository cannot
    be interpreted correctly.
    """


# Generic words that should not make two scenarios
# appear relevant merely because they describe monitoring
# properties using common vocabulary.
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "detect",
    "detected",
    "detecting",
    "detection",
    "for",
    "from",
    "in",
    "into",
    "is",
    "message",
    "messages",
    "monitor",
    "monitoring",
    "of",
    "on",
    "or",
    "property",
    "request",
    "requests",
    "rule",
    "same",
    "scenario",
    "the",
    "to",
    "traffic",
    "using",
    "with",
    "5g",
    "condition",
    "conditions",
    "event",
    "events",
}


def _tokens(
    text: str,
) -> set[str]:
    """
    Normalize free text and metadata into lexical terms.
    """

    normalized = (
        text
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
    )

    values = re.findall(
        r"[a-z0-9]+",
        normalized,
    )

    return {
        value
        for value in values
        if (
            len(value) >= 2
            and value not in STOPWORDS
        )
    }


def _protocol_tokens(
    protocols: set[str],
) -> set[str]:
    """
    Return lexical tokens corresponding to protocol
    names so protocol matching is not counted again
    as semantic text similarity.
    """

    result = set()

    for protocol in protocols:
        result.update(
            _tokens(protocol)
        )

    return result


def _task_text(
    task: MonitoringTask,
) -> str:
    """
    Build the text used for semantic metadata matching.

    Restrictions are deliberately not used because a
    prohibited concept should not make an example more
    relevant.
    """

    parts = [
        task.description,
    ]

    parts.extend(
        task.requirements
    )

    if task.expected_behavior:
        parts.append(
            task.expected_behavior
        )

    return " ".join(
        str(part)
        for part in parts
        if part
    )


class VerifiedExampleRetriever:
    """
    Deterministic retriever for curated MMT property
    examples.

    Retrieval steps:

    1. keep only validated examples;
    2. require protocol overlap;
    3. rank using protocol coverage and lexical metadata
       relevance;
    4. apply a minimum relevance score;
    5. load XML only for the selected examples.

    Results are cached by task content so retrieval is
    stable for repeated use of the same task.
    """

    def __init__(
        self,
        config: RetrievalConfig | None = None,
        index_loader: Callable[
            [],
            list[dict],
        ] = load_example_index,
        property_loader: Callable[
            [str],
            str,
        ] = load_property_example,
    ):
        self.config = (
            config
            or RetrievalConfig()
        )

        self.index_loader = (
            index_loader
        )

        self.property_loader = (
            property_loader
        )

        self._cache: dict[
            str,
            RetrievalResult,
        ] = {}

    def clear_cache(
        self,
    ) -> None:
        """
        Clear task-level retrieval cache.

        Useful between independent experimental runs.
        """

        self._cache.clear()

    def _cache_key(
        self,
        task: MonitoringTask,
    ) -> str:
        payload = {
            "task":
                task.model_dump(
                    mode="json"
                ),
            "retrieval_config":
                self.config.model_dump(
                    mode="json"
                ),
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
        ).encode(
            "utf-8"
        )

        return hashlib.sha256(
            encoded
        ).hexdigest()

    def _load_metadata(
        self,
    ) -> list[VerifiedExampleMetadata]:

        raw_index = (
            self.index_loader()
        )

        examples = []

        for raw_entry in raw_index:
            try:
                examples.append(
                    VerifiedExampleMetadata
                    .model_validate(
                        raw_entry
                    )
                )

            except ValidationError as exc:
                raise ExampleRetrievalError(
                    "Invalid entry in verified "
                    "example index."
                ) from exc

        return examples

    def retrieve(
        self,
        task: MonitoringTask,
    ) -> RetrievalResult:
        """
        Retrieve at most k verified examples for one
        monitoring task.
        """

        cache_key = self._cache_key(
            task
        )

        cached = self._cache.get(
            cache_key
        )

        if cached is not None:
            return cached.model_copy(
                deep=True
            )

        if not self.config.enabled:
            result = RetrievalResult(
                task_id=task.id,
                enabled=False,
                requested_k=(
                    self.config.k
                ),
                candidate_count=0,
                examples=[],
                metadata={
                    "reason":
                        "retrieval_disabled"
                },
            )

            self._cache[
                cache_key
            ] = result

            return result.model_copy(
                deep=True
            )

        task_protocols = {
            protocol.lower()
            for protocol
            in task.protocols
        }

        if not task_protocols:
            result = RetrievalResult(
                task_id=task.id,
                enabled=True,
                requested_k=(
                    self.config.k
                ),
                candidate_count=0,
                examples=[],
                metadata={
                    "reason":
                        "task_has_no_protocols"
                },
            )

            self._cache[
                cache_key
            ] = result

            return result.model_copy(
                deep=True
            )

        protocol_terms = (
            _protocol_tokens(
                task_protocols
            )
        )

        task_terms = (
            _tokens(
                _task_text(task)
            )
            - protocol_terms
        )

        scored_candidates = []

        candidate_count = 0

        for example in (
            self._load_metadata()
        ):
            if not example.validated:
                continue

            example_protocols = {
                protocol.lower()
                for protocol
                in example.protocols
            }

            matched_protocols = (
                task_protocols
                & example_protocols
            )

            # Protocol compatibility is mandatory.
            if not matched_protocols:
                continue

            candidate_count += 1

            protocol_score = (
                len(matched_protocols)
                / len(task_protocols)
            )

            example_protocol_terms = (
                _protocol_tokens(
                    example_protocols
                )
            )

            searchable_text = " ".join(
                [
                    example.description,
                    *example.tags,
                    *example.constructs,
                ]
            )

            example_terms = (
                _tokens(
                    searchable_text
                )
                - protocol_terms
                - example_protocol_terms
            )

            matched_terms = (
                task_terms
                & example_terms
            )

            if (
                len(matched_terms)
                < self.config.min_semantic_matches
            ):
                continue

            if task_terms:
                denominator = min(
                    len(task_terms),
                    8,
                )

                text_score = min(
                    1.0,
                    (
                        len(matched_terms)
                        / denominator
                    ),
                )

            else:
                text_score = 0.0

            # Protocol compatibility and scenario
            # relevance contribute equally.
            score = (
                0.5
                * protocol_score
                + 0.5
                * text_score
            )

            score = round(
                score,
                4,
            )

            if (
                score
                < self.config.min_score
            ):
                continue

            matched_tags = []

            for tag in example.tags:
                tag_terms = (
                    _tokens(tag)
                    - example_protocol_terms
                    - protocol_terms
                )

                if (
                    tag_terms
                    & task_terms
                ):
                    matched_tags.append(
                        tag
                    )

            scored_candidates.append(
                {
                    "metadata":
                        example,
                    "score":
                        score,
                    "matched_protocols":
                        sorted(
                            matched_protocols
                        ),
                    "matched_terms":
                        sorted(
                            matched_terms
                        ),
                    "matched_tags":
                        sorted(
                            matched_tags
                        ),
                }
            )

        # Deterministic ranking.
        scored_candidates.sort(
            key=lambda candidate: (
                -candidate["score"],
                -len(
                    candidate[
                        "matched_protocols"
                    ]
                ),
                candidate[
                    "metadata"
                ].property_id,
            )
        )

        selected = (
            scored_candidates[
                :self.config.k
            ]
        )

        retrieved_examples = []

        for candidate in selected:
            metadata = candidate[
                "metadata"
            ]

            try:
                xml = (
                    self.property_loader(
                        metadata.file
                    )
                )

            except Exception as exc:
                raise ExampleRetrievalError(
                    "Unable to load verified "
                    f"property example "
                    f"'{metadata.property_id}'."
                ) from exc

            retrieved_examples.append(
                RetrievedExample(
                    property_id=(
                        metadata.property_id
                    ),
                    file=metadata.file,
                    property_type=(
                        metadata.property_type
                    ),
                    description=(
                        metadata.description
                    ),
                    protocols=(
                        metadata.protocols
                    ),
                    tags=metadata.tags,
                    constructs=(
                        metadata.constructs
                    ),
                    score=(
                        candidate["score"]
                    ),
                    matched_protocols=(
                        candidate[
                            "matched_protocols"
                        ]
                    ),
                    matched_terms=(
                        candidate[
                            "matched_terms"
                        ]
                    ),
                    matched_tags=(
                        candidate[
                            "matched_tags"
                        ]
                    ),
                    xml=xml,
                )
            )

        result = RetrievalResult(
            task_id=task.id,
            enabled=True,
            requested_k=(
                self.config.k
            ),
            candidate_count=(
                candidate_count
            ),
            examples=(
                retrieved_examples
            ),
            metadata={
                "min_score":
                    self.config.min_score,
                "scoring": {
                    "protocol_weight":
                        0.5,
                    "text_weight":
                        0.5,
                },
            },
        )

        self._cache[
            cache_key
        ] = result

        return result.model_copy(
            deep=True
        )