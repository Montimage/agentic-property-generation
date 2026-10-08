from __future__ import annotations

from dataclasses import dataclass

from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    SemanticAssessment,
)


@dataclass(frozen=True)
class SemanticGuardAction:
    """
    One deterministic normalization performed on an
    LLM-produced semantic assessment.
    """

    source_dimension: str
    target_dimension: str
    original_type: str
    normalized_type: str
    message: str


@dataclass(frozen=True)
class SemanticGuardResult:
    """
    Result of deterministic semantic-assessment
    normalization.

    The original LLM assessment is not mutated.
    """

    assessment: SemanticAssessment
    actions: tuple[SemanticGuardAction, ...]


class SemanticAssessmentGuard:
    """
    Deterministically normalize an LLM-produced
    SemanticAssessment.

    This component does not perform semantic reasoning.

    It only enforces semantic-output consistency rules
    whose scope is already defined by the workflow.

    In particular, embedded-function implementation
    defects belong to Detection Semantics rather than
    leaking into unrelated semantic dimensions.
    """

    _NON_DETECTION_DIMENSIONS = (
        "message_exchange_semantics",
        "temporal_ordering_semantics",
        "attribute_relevance",
    )

    _MOVABLE_ISSUE_TYPES = {
        "property_logic_error",
        "semantic_mismatch",
    }

    _EMBEDDED_LOGIC_MARKERS = (
        "embedded function",
        "embedded-function",
        "#em_",
        "em_",
        "security_c_type",
    )

    def normalize(
        self,
        task: MonitoringTask,
        generated_property: GeneratedProperty,
        assessment: SemanticAssessment,
    ) -> SemanticGuardResult:
        """
        Normalize one semantic assessment.

        The task is accepted explicitly because later
        guard rules may use deterministic facts already
        represented in the canonical MonitoringTask.

        Version 1 deliberately does not infer new task or
        protocol semantics.
        """

        del task

        data = assessment.model_dump(
            mode="json"
        )

        # The embedded-function cross-dimension rule is
        # irrelevant when the current property contains
        # no embedded C.
        if not self._has_embedded_functions(
            generated_property
        ):
            return SemanticGuardResult(
                assessment=assessment,
                actions=(),
            )

        actions: list[
            SemanticGuardAction
        ] = []

        moved_issues: list[dict] = []

        moved_source_scores: list[float] = []

        for dimension_name in (
            self._NON_DETECTION_DIMENSIONS
        ):
            dimension = data[
                dimension_name
            ]

            source_score = float(
                dimension.get(
                    "score",
                    1.0,
                )
            )

            original_issues = list(
                dimension.get(
                    "issues",
                    [],
                )
            )

            remaining_issues = []

            moved_from_dimension = []

            for issue in original_issues:
                if (
                    self
                    ._is_embedded_detection_issue(
                        issue
                    )
                ):
                    normalized_issue = (
                        dict(issue)
                    )

                    original_type = str(
                        normalized_issue.get(
                            "type",
                            "",
                        )
                    )

                    # Embedded executable-logic defects
                    # are represented consistently as
                    # PROPERTY_LOGIC_ERROR.
                    normalized_issue[
                        "type"
                    ] = (
                        "property_logic_error"
                    )

                    moved_issues.append(
                        normalized_issue
                    )

                    moved_from_dimension.append(
                        normalized_issue
                    )

                    actions.append(
                        SemanticGuardAction(
                            source_dimension=(
                                dimension_name
                            ),
                            target_dimension=(
                                "detection_semantics"
                            ),
                            original_type=(
                                original_type
                            ),
                            normalized_type=(
                                "property_logic_error"
                            ),
                            message=str(
                                normalized_issue.get(
                                    "message",
                                    "",
                                )
                            ),
                        )
                    )

                else:
                    remaining_issues.append(
                        issue
                    )

            if moved_from_dimension:
                moved_source_scores.append(
                    source_score
                )

                dimension[
                    "issues"
                ] = remaining_issues

                # If every reported problem in this
                # dimension was actually an embedded
                # detection-logic problem, the lowered
                # score was caused only by cross-dimension
                # leakage.
                if not remaining_issues:
                    dimension[
                        "score"
                    ] = 1.0

                    dimension[
                        "justification"
                    ] = (
                        "No independent semantic issue "
                        "remains in this dimension after "
                        "deterministic normalization of "
                        "embedded-function implementation "
                        "issues."
                    )

        if moved_issues:
            detection = data[
                "detection_semantics"
            ]

            detection[
                "score"
            ] = min(
                float(
                    detection.get(
                        "score",
                        1.0,
                    )
                ),
                *moved_source_scores,
            )

            combined = (
                list(
                    detection.get(
                        "issues",
                        [],
                    )
                )
                + moved_issues
            )

            detection[
                "issues"
            ] = self._deduplicate_issues(
                combined
            )

            existing_justification = str(
                detection.get(
                    "justification",
                    "",
                )
            ).strip()

            normalization_note = (
                "Embedded-function implementation issues "
                "reported in other semantic dimensions "
                "were normalized into Detection Semantics."
            )

            if existing_justification:
                detection[
                    "justification"
                ] = (
                    existing_justification
                    + " "
                    + normalization_note
                )
            else:
                detection[
                    "justification"
                ] = normalization_note

            data[
                "summary"
            ] = self._build_summary(
                data
            )

        normalized = (
            SemanticAssessment.model_validate(
                data
            )
        )

        return SemanticGuardResult(
            assessment=normalized,
            actions=tuple(actions),
        )

    @classmethod
    def _is_embedded_detection_issue(
        cls,
        issue: dict,
    ) -> bool:
        """
        Return True only for issues that explicitly refer
        to embedded-function executable logic.

        This intentionally uses a narrow rule.

        It does not attempt to infer the semantics of
        arbitrary C code.
        """

        issue_type = str(
            issue.get(
                "type",
                "",
            )
        ).lower()

        if (
            issue_type
            not in cls._MOVABLE_ISSUE_TYPES
        ):
            return False

        message = str(
            issue.get(
                "message",
                "",
            )
        )

        evidence = str(
            issue.get(
                "evidence",
                "",
            )
        )

        text = (
            message
            + "\n"
            + evidence
        ).lower()

        return any(
            marker in text
            for marker
            in cls._EMBEDDED_LOGIC_MARKERS
        )

    @staticmethod
    def _has_embedded_functions(
        generated_property: GeneratedProperty,
    ) -> bool:
        return (
            "<embedded_functions"
            in generated_property.xml.lower()
        )

    @staticmethod
    def _deduplicate_issues(
        issues: list[dict],
    ) -> list[dict]:
        """
        Remove exact semantic-issue duplicates while
        preserving their first occurrence.
        """

        result = []

        seen = set()

        for issue in issues:
            key = (
                str(
                    issue.get(
                        "type",
                        "",
                    )
                ),
                str(
                    issue.get(
                        "message",
                        "",
                    )
                ),
                str(
                    issue.get(
                        "evidence",
                        "",
                    )
                ),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(issue)

        return result

    @staticmethod
    def _build_summary(
        data: dict,
    ) -> str:
        """
        Build a neutral deterministic summary from the
        remaining normalized issues.

        This avoids retaining a summary that refers to
        issues removed from their original dimensions.
        """

        messages = []

        seen = set()

        for dimension_name in (
            "message_exchange_semantics",
            "temporal_ordering_semantics",
            "detection_semantics",
            "attribute_relevance",
        ):
            dimension = data[
                dimension_name
            ]

            for issue in dimension.get(
                "issues",
                [],
            ):
                message = str(
                    issue.get(
                        "message",
                        "",
                    )
                ).strip()

                if (
                    not message
                    or message in seen
                ):
                    continue

                seen.add(message)
                messages.append(message)

        if not messages:
            return (
                "No semantic issues remain after "
                "deterministic semantic-assessment "
                "normalization."
            )

        return (
            "Semantic assessment normalized "
            "deterministically. Remaining issues: "
            + " | ".join(messages)
        )