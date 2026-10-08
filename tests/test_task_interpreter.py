from types import SimpleNamespace

import pytest

from property_agent.agents import (
    TaskInterpretationError,
    TaskInterpreter,
    extract_interpretation_json,
)

from property_agent.llm import (
    LLMResponse,
)

from property_agent.models import (
    NaturalLanguageScenario,
)


class FakeTaskInterpreterLLMClient:
    """
    Fake LLM used to test natural-language task
    interpretation without an external model.
    """

    def __init__(
        self,
        content: str | None = None,
    ):
        self.config = SimpleNamespace(
            model="fake/interpreter-model"
        )

        self.received_messages = None

        self.content = (
            content
            if content is not None
            else """
{
  "description": "Detect an abnormal number of registration-related NGAP requests originating from the same source within a limited time window.",
  "protocols": [
    "ngap"
  ],
  "monitoring_point": null,
  "requirements": [
    "Detect an abnormal number of registration-related requests.",
    "The requests must originate from the same source.",
    "Evaluate the requests within a limited time window."
  ],
  "restrictions": [],
  "expected_behavior": "Identify abnormal repeated registration-related requests from the same source within a limited period.",
  "ambiguities": [
    "The numerical threshold defining an abnormal number of requests is not specified.",
    "The duration of the limited time window is not specified.",
    "The task does not define how the same source should be represented."
  ]
}
"""
        )

    def complete(
        self,
        messages,
    ):
        self.received_messages = messages

        return LLMResponse(
            content=self.content,
            model=(
                "fake/interpreter-provider"
            ),
            usage={
                "prompt_tokens": 300,
                "completion_tokens": 150,
            },
        )


def make_scenario():
    return NaturalLanguageScenario(
        id="nl_task_001",
        property_id="201",
        text=(
            "Monitor NGAP traffic and detect an "
            "abnormal number of registration-related "
            "requests from the same source within a "
            "limited time window."
        ),
    )


def test_extract_interpretation_json():
    content = """
    ```json
    {
        "description": "Example"
    }
    ```
    """

    result = (
        extract_interpretation_json(
            content
        )
    )

    assert result.startswith("{")
    assert result.endswith("}")


def test_task_interpreter_builds_monitoring_task():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    interpreter = TaskInterpreter(
        client=client
    )

    result = interpreter.interpret(
        make_scenario()
    )

    task = result.task

    assert task.id == "nl_task_001"

    assert task.property_id == "201"

    assert task.protocols == [
        "ngap"
    ]

    assert len(
        task.ambiguities
    ) == 3

    assert (
        "threshold"
        in task.ambiguities[0]
    )

    assert (
        "duration"
        in task.ambiguities[1]
    )

    assert (
        "same source"
        in task.ambiguities[2]
    )


def test_task_interpreter_preserves_external_ids():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    interpreter = TaskInterpreter(
        client=client
    )

    result = interpreter.interpret(
        make_scenario()
    )

    assert (
        result.task.id
        == "nl_task_001"
    )

    assert (
        result.task.property_id
        == "201"
    )


def test_task_interpreter_preserves_original_text():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    scenario = make_scenario()

    interpreter = TaskInterpreter(
        client=client
    )

    result = interpreter.interpret(
        scenario
    )

    assert (
        result.task.metadata[
            "input"
        ]["mode"]
        == "natural_language"
    )

    assert (
        result.task.metadata[
            "input"
        ]["original_text"]
        == scenario.text
    )


def test_interpreter_receives_available_protocols():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    interpreter = TaskInterpreter(
        client=client
    )

    interpreter.interpret(
        make_scenario()
    )

    system_message = (
        client.received_messages[
            0
        ]["content"]
    )

    assert (
        "AVAILABLE PROTOCOLS"
        in system_message
    )

    assert "ngap" in system_message


def test_interpreter_is_instructed_not_to_resolve_ambiguities():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    interpreter = TaskInterpreter(
        client=client
    )

    interpreter.interpret(
        make_scenario()
    )

    system_message = (
        client.received_messages[
            0
        ]["content"]
    )

    assert (
        "Do not resolve ambiguities yourself"
        in system_message
    )

    assert (
        "Do not invent"
        in system_message
    )


def test_invalid_interpretation_json():
    client = (
        FakeTaskInterpreterLLMClient(
            content="Not JSON."
        )
    )

    interpreter = TaskInterpreter(
        client=client
    )

    with pytest.raises(
        TaskInterpretationError
    ):
        interpreter.interpret(
            make_scenario()
        )

def test_task_interpreter_receives_user_clarifications():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    interpreter = TaskInterpreter(
        client=client
    )

    scenario = NaturalLanguageScenario(
        id="nl_task_clarified",
        property_id="202",
        text=(
            "Detect an abnormal number of "
            "NGAP requests within a limited "
            "time window."
        ),
        clarifications=[
            (
                "Consider more than 10 requests "
                "within 5 seconds abnormal."
            )
        ],
    )

    interpreter.interpret(
        scenario
    )

    user_message = (
        client.received_messages[
            1
        ]["content"]
    )

    assert (
        "USER CLARIFICATIONS"
        in user_message
    )

    assert (
        "more than 10 requests"
        in user_message
    )

    assert (
        "5 seconds"
        in user_message
    )

def test_task_interpreter_preserves_clarifications_in_metadata():
    client = (
        FakeTaskInterpreterLLMClient()
    )

    interpreter = TaskInterpreter(
        client=client
    )

    scenario = NaturalLanguageScenario(
        id="nl_task_clarified",
        property_id="202",
        text="Monitor NGAP traffic.",
        clarifications=[
            "Use a 5-second time window."
        ],
    )

    result = interpreter.interpret(
        scenario
    )

    assert (
        result.task.metadata[
            "input"
        ]["clarifications"]
        == [
            "Use a 5-second time window."
        ]
    )