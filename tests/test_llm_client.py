from types import SimpleNamespace

from property_agent.llm import (
    LLMClient,
    LLMConfig,
)


def test_llm_client(monkeypatch):

    fake_response = SimpleNamespace(
        model="test-provider-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        "<beginning>"
                        "<property></property>"
                        "</beginning>"
                    )
                )
            )
        ],
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 20,
        },
    )

    captured_kwargs = {}

    def fake_completion(**kwargs):
        captured_kwargs.update(kwargs)
        return fake_response

    monkeypatch.setattr(
        "property_agent.llm.client.completion",
        fake_completion,
    )

    config = LLMConfig(
        model="ollama/test-model",
        api_base="http://localhost:11434",
        temperature=0.0,
    )

    client = LLMClient(config)

    response = client.complete(
        [
            {
                "role": "user",
                "content": "test",
            }
        ]
    )

    assert (
        response.content
        == "<beginning><property></property></beginning>"
    )

    assert (
        captured_kwargs["model"]
        == "ollama/test-model"
    )

    assert (
        captured_kwargs["api_base"]
        == "http://localhost:11434"
    )