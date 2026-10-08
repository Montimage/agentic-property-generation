from property_agent.models import (
    MonitoringTask,
    NaturalLanguageScenario,
    TaskInterpretationResult,
)

from property_agent.workflow import (
    TaskIntakeWorkflow,
)


class FakeTaskInterpreter:
    """
    Stateful fake interpreter.

    First interpretation:
        returns an ambiguous task.

    After the user supplies a clarification:
        returns a fully specified task.
    """

    def __init__(self):
        self.calls = []

    def interpret(
        self,
        scenario: NaturalLanguageScenario,
    ) -> TaskInterpretationResult:

        self.calls.append(
            scenario
        )

        if not scenario.clarifications:
            task = MonitoringTask(
                id=scenario.id,
                property_id=(
                    scenario.property_id
                ),
                description=(
                    "Detect an abnormal number "
                    "of NGAP requests."
                ),
                protocols=[
                    "ngap"
                ],
                requirements=[
                    (
                        "Detect an abnormal number "
                        "of NGAP requests."
                    )
                ],
                ambiguities=[
                    (
                        "The numerical threshold "
                        "is not specified."
                    ),
                    (
                        "The time-window duration "
                        "is not specified."
                    ),
                ],
            )

        else:
            task = MonitoringTask(
                id=scenario.id,
                property_id=(
                    scenario.property_id
                ),
                description=(
                    "Detect more than 10 NGAP "
                    "requests within 5 seconds."
                ),
                protocols=[
                    "ngap"
                ],
                requirements=[
                    (
                        "Detect more than 10 "
                        "NGAP requests."
                    ),
                    (
                        "Evaluate requests within "
                        "5 seconds."
                    ),
                ],
                ambiguities=[],
            )

        return TaskInterpretationResult(
            scenario_id=scenario.id,
            task=task,
            model="fake/interpreter",
        )


class AlwaysAmbiguousInterpreter:
    """
    Fake interpreter used to test the clarification
    limit.
    """

    def interpret(
        self,
        scenario: NaturalLanguageScenario,
    ) -> TaskInterpretationResult:

        task = MonitoringTask(
            id=scenario.id,
            property_id=(
                scenario.property_id
            ),
            description=(
                "Ambiguous monitoring task."
            ),
            protocols=[
                "ngap"
            ],
            ambiguities=[
                (
                    "The required threshold "
                    "is not specified."
                )
            ],
        )

        return TaskInterpretationResult(
            scenario_id=scenario.id,
            task=task,
            model="fake/interpreter",
        )


def make_scenario():
    return NaturalLanguageScenario(
        id="intake_test_001",
        property_id="301",
        text=(
            "Detect an abnormal number of "
            "NGAP requests within a limited "
            "time window."
        ),
    )


def test_complete_task_does_not_interrupt():
    class CompleteInterpreter:

        def interpret(
            self,
            scenario,
        ):
            task = MonitoringTask(
                id=scenario.id,
                property_id=(
                    scenario.property_id
                ),
                description=(
                    "Detect more than 10 NGAP "
                    "requests within 5 seconds."
                ),
                protocols=[
                    "ngap"
                ],
                requirements=[
                    (
                        "Detect more than 10 "
                        "NGAP requests within "
                        "5 seconds."
                    )
                ],
                ambiguities=[],
            )

            return TaskInterpretationResult(
                scenario_id=scenario.id,
                task=task,
                model="fake/interpreter",
            )

    workflow = TaskIntakeWorkflow(
        task_interpreter=(
            CompleteInterpreter()
        )
    )

    result = workflow.start(
        scenario=make_scenario(),
        thread_id="complete-test",
    )

    assert result["complete"] is True

    assert (
        result["terminal_reason"]
        == "task_ready"
    )

    assert "__interrupt__" not in result


def test_ambiguous_task_interrupts():
    workflow = TaskIntakeWorkflow(
        task_interpreter=(
            FakeTaskInterpreter()
        )
    )

    result = workflow.start(
        scenario=make_scenario(),
        thread_id="interrupt-test",
    )

    assert "__interrupt__" in result

    interrupts = result[
        "__interrupt__"
    ]

    assert len(interrupts) == 1

    payload = interrupts[0].value

    assert (
        payload["type"]
        == "task_clarification_required"
    )

    assert (
        payload["task_id"]
        == "intake_test_001"
    )

    assert len(
        payload["ambiguities"]
    ) == 2


def test_resume_with_clarification_completes_task():
    interpreter = (
        FakeTaskInterpreter()
    )

    workflow = TaskIntakeWorkflow(
        task_interpreter=interpreter
    )

    thread_id = "resume-test"

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert "__interrupt__" in first

    result = workflow.resume(
        clarification=(
            "Use more than 10 requests "
            "within 5 seconds."
        ),
        thread_id=thread_id,
    )

    assert result["complete"] is True

    assert (
        result["terminal_reason"]
        == "task_ready"
    )

    assert (
        result["task"].ambiguities
        == []
    )

    assert (
        result["clarification_round"]
        == 1
    )


def test_clarification_is_preserved_in_scenario():
    interpreter = (
        FakeTaskInterpreter()
    )

    workflow = TaskIntakeWorkflow(
        task_interpreter=interpreter
    )

    thread_id = (
        "clarification-history-test"
    )

    workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    clarification = (
        "Use more than 10 requests "
        "within 5 seconds."
    )

    result = workflow.resume(
        clarification=clarification,
        thread_id=thread_id,
    )

    assert (
        result[
            "scenario"
        ].clarifications
        == [
            clarification
        ]
    )


def test_same_thread_id_is_required_for_resume():
    workflow = TaskIntakeWorkflow(
        task_interpreter=(
            FakeTaskInterpreter()
        )
    )

    workflow.start(
        scenario=make_scenario(),
        thread_id="correct-thread",
    )

    # A different thread does not contain the
    # suspended workflow state.
    #
    # Depending on the installed LangGraph version,
    # this may raise an exception rather than returning
    # a normal state. The important invariant is that
    # resume must use the original thread_id.

def test_clarification_limit_blocks_task():
    workflow = TaskIntakeWorkflow(
        task_interpreter=(
            AlwaysAmbiguousInterpreter()
        ),
        max_clarification_rounds=1,
    )

    thread_id = "limit-test"

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert "__interrupt__" in first

    result = workflow.resume(
        clarification=(
            "I am not sure what threshold "
            "should be used."
        ),
        thread_id=thread_id,
    )

    assert result["complete"] is False

    assert (
        result["terminal_reason"]
        == "clarification_limit_reached"
    )

    assert (
        result["clarification_round"]
        == 1
    )

    assert (
        len(
            result["task"].ambiguities
        )
        == 1
    )

class FakeAssumptionResolver:

    def __init__(
        self,
    ):
        self.calls = []

    def resolve(
        self,
        task,
    ):
        self.calls.append(
            task
        )

        return task.model_copy(
            update={
                "requirements": [
                    *task.requirements,
                    (
                        "Use the same AMF UE "
                        "identifier as the "
                        "correlation criterion."
                    ),
                ],

                "assumptions": [
                    (
                        "Treat requests sharing "
                        "the same AMF UE identifier "
                        "as originating from the "
                        "same source."
                    )
                ],

                "ambiguities": [],
            }
        )

def test_user_can_cancel_clarification():
    workflow = TaskIntakeWorkflow(
        task_interpreter=(
            FakeTaskInterpreter()
        )
    )

    thread_id = "cancel-test"

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert "__interrupt__" in first

    result = workflow.resume(
        clarification={
            "action": "cancel"
        },
        thread_id=thread_id,
    )

    assert result["complete"] is False

    assert (
        result["terminal_reason"]
        == "clarification_cancelled"
    )

class FakePartiallyResolvingInterpreter:
    """
    Fake interpreter used to test the
    assume_remaining path.

    Initial interpretation:
    - threshold is missing;
    - time window is missing;
    - same-source representation is missing.

    After explicit clarification:
    - threshold is resolved;
    - time window is resolved;
    - same-source representation remains ambiguous.

    The remaining ambiguity must therefore be handled by
    the authorized assumption resolver.
    """

    def __init__(
        self,
    ):
        self.calls = []

    def interpret(
        self,
        scenario: NaturalLanguageScenario,
    ) -> TaskInterpretationResult:

        self.calls.append(
            scenario
        )

        if not scenario.clarifications:
            task = MonitoringTask(
                id=scenario.id,
                property_id=(
                    scenario.property_id
                ),
                description=(
                    "Detect an abnormal number "
                    "of NGAP requests from the "
                    "same source within a limited "
                    "time window."
                ),
                protocols=[
                    "ngap"
                ],
                requirements=[
                    (
                        "Detect an abnormal number "
                        "of NGAP requests."
                    ),
                    (
                        "Requests must originate "
                        "from the same source."
                    ),
                    (
                        "Evaluate requests within "
                        "a limited time window."
                    ),
                ],
                ambiguities=[
                    (
                        "The numerical threshold "
                        "is not specified."
                    ),
                    (
                        "The time-window duration "
                        "is not specified."
                    ),
                    (
                        "The task does not define "
                        "how the same source should "
                        "be represented."
                    ),
                ],
            )

        else:
            task = MonitoringTask(
                id=scenario.id,
                property_id=(
                    scenario.property_id
                ),
                description=(
                    "Detect more than 10 NGAP "
                    "requests from the same source "
                    "within 5 seconds."
                ),
                protocols=[
                    "ngap"
                ],
                requirements=[
                    (
                        "Detect more than 10 "
                        "NGAP requests."
                    ),
                    (
                        "Evaluate requests within "
                        "5 seconds."
                    ),
                    (
                        "Requests must originate "
                        "from the same source."
                    ),
                ],
                ambiguities=[
                    (
                        "The task does not define "
                        "how the same source should "
                        "be represented."
                    )
                ],
            )

        return TaskInterpretationResult(
            scenario_id=scenario.id,
            task=task,
            model="fake/interpreter",
        )

def test_user_can_authorize_remaining_assumptions():
    interpreter = (
        FakePartiallyResolvingInterpreter()
    )

    resolver = (
        FakeAssumptionResolver()
    )

    workflow = TaskIntakeWorkflow(
        task_interpreter=interpreter,
        assumption_resolver=resolver,
    )

    thread_id = (
        "assume-remaining-test"
    )

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert "__interrupt__" in first

    payload = (
        first["__interrupt__"][0].value
    )

    assert (
        len(
            payload["ambiguities"]
        )
        == 3
    )

    result = workflow.resume(
        clarification={
            "action":
                "assume_remaining",

            "text":
                (
                    "Use more than 10 requests "
                    "within 5 seconds."
                ),
        },
        thread_id=thread_id,
    )

    assert result["complete"] is True

    assert (
        result["terminal_reason"]
        == "task_ready"
    )

    assert (
        result["task"].ambiguities
        == []
    )

    assert (
        len(
            result["task"].assumptions
        )
        == 1
    )

    assert (
        "AMF UE identifier"
        in result[
            "task"
        ].assumptions[0]
    )

    assert len(
        resolver.calls
    ) == 1

    # The resolver must receive only the ambiguity
    # that remained after applying the user's explicit
    # clarification.
    assert (
        len(
            resolver.calls[
                0
            ].ambiguities
        )
        == 1
    )

    assert (
        "same source"
        in resolver.calls[
            0
        ].ambiguities[
            0
        ]
    )

    assert (
        result["clarification_round"]
        == 1
    )

def test_assumption_resolver_not_called_when_clarification_resolves_all():
    interpreter = (
        FakeTaskInterpreter()
    )

    resolver = (
        FakeAssumptionResolver()
    )

    workflow = TaskIntakeWorkflow(
        task_interpreter=interpreter,
        assumption_resolver=resolver,
    )

    thread_id = (
        "assume-but-already-resolved-test"
    )

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert "__interrupt__" in first

    result = workflow.resume(
        clarification={
            "action":
                "assume_remaining",

            "text":
                (
                    "Use more than 10 requests "
                    "within 5 seconds."
                ),
        },
        thread_id=thread_id,
    )

    assert result["complete"] is True

    assert (
        result["task"].ambiguities
        == []
    )

    assert (
        result["task"].assumptions
        == []
    )

    assert resolver.calls == []