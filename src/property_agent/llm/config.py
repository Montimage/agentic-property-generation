from typing import Any

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """
    Configuration for an LLM used by the property-generation system.

    The model name follows LiteLLM's provider/model convention,
    for example:

        ollama/qwen2.5-coder:7b
        openai/gpt-5
        anthropic/claude-sonnet-4-5-20250929
    """

    model: str = Field(
        ...,
        description="LiteLLM model identifier.",
    )

    temperature: float | None = Field(
        default=0.0,
        ge=0.0,
        description="Sampling temperature when supported by the model.",
    )

    max_tokens: int | None = Field(
        default=4096,
        gt=0,
        description="Maximum number of output tokens.",
    )

    api_base: str | None = Field(
        default=None,
        description="Optional API endpoint, e.g. a local Ollama server.",
    )

    timeout: float | None = Field(
        default=300.0,
        gt=0,
        description="Maximum request duration in seconds.",
    )

    extra_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific LiteLLM arguments.",
    )