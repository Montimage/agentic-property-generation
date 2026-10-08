from collections.abc import Callable
from dataclasses import dataclass

from property_agent.agents import (
    PropertyGenerator,
    PropertyRepairer,
    SemanticReviewer,
)

from property_agent.models import (
    ValidationResult,
)

from property_agent.retrieval import (
    VerifiedExampleRetriever,
)

from property_agent.tools import (
    MMTCompilationClient,
)


ValidatorFunction = Callable[
    [str],
    ValidationResult,
]


@dataclass
class WorkflowDependencies:
    """
    Components used by the LangGraph workflow.

    LangGraph orchestrates these components but does not
    replace their internal implementations.
    """

    generator: PropertyGenerator

    semantic_reviewer: SemanticReviewer

    repairer: PropertyRepairer

    retriever: VerifiedExampleRetriever

    compilation_client: MMTCompilationClient

    xml_validator: ValidatorFunction

    syntax_validator: ValidatorFunction

    static_validator: ValidatorFunction