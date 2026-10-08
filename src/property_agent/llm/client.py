from dataclasses import dataclass
from typing import Any

from litellm import completion

from .config import LLMConfig


class LLMClientError(RuntimeError):
    """Raised when an LLM request cannot be completed."""


@dataclass
class LLMResponse:
    """
    Normalized response returned by the LLM client.
    """

    content: str
    model: str
    usage: dict[str, Any]


class LLMClient:
    """
    Provider-independent LLM client implemented using LiteLLM.
    """

    def __init__(self, config: LLMConfig):
        self.config = config

    def complete(
        self,
        messages: list[dict[str, str]],
    ) -> LLMResponse:
        """
        Send a chat-completion request and normalize the response.
        """

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }

        # Provider-specific or optional arguments may be supplied here.
        kwargs.update(self.config.extra_kwargs)

        # Explicit configuration values take precedence over extra_kwargs.
        if self.config.temperature is not None:
            kwargs["temperature"] = (
                self.config.temperature
            )

        if self.config.max_tokens is not None:
            kwargs["max_tokens"] = (
                self.config.max_tokens
            )

        if self.config.api_base is not None:
            kwargs["api_base"] = (
                self.config.api_base
            )

        if self.config.timeout is not None:
            kwargs["timeout"] = (
                self.config.timeout
            )

        try:
            response = completion(
                **kwargs
            )

        except Exception as exc:
            timeout_info = ""

            if self.config.timeout is not None:
                timeout_info = (
                    f" after a configured timeout of "
                    f"{self.config.timeout} seconds"
                )

            raise LLMClientError(
                f"LLM request failed for model "
                f"'{self.config.model}'"
                f"{timeout_info}: {exc}"
            ) from exc

        try:
            content = (
                response
                .choices[0]
                .message
                .content
            )

        except (
            AttributeError,
            IndexError,
            TypeError,
        ) as exc:
            raise LLMClientError(
                "The LLM response did not contain "
                "an assistant message."
            ) from exc

        if not content:
            raise LLMClientError(
                "The LLM returned an empty response."
            )

        response_model = getattr(
            response,
            "model",
            self.config.model,
        )

        usage_data: dict[str, Any] = {}

        usage = getattr(
            response,
            "usage",
            None,
        )

        if usage is not None:
            if hasattr(
                usage,
                "model_dump",
            ):
                usage_data = (
                    usage.model_dump()
                )

            elif isinstance(
                usage,
                dict,
            ):
                usage_data = usage

        return LLMResponse(
            content=content,
            model=response_model,
            usage=usage_data,
        )