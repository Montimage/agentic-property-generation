from property_agent.models import (
    MonitoringTask,
    NaturalLanguageScenario,
    NaturalLanguageWorkflowStatus,
    PropertyGenerationResult,
    TaskInterpretationResult,
)

from property_agent.workflow import (
    NaturalLanguagePropertyWorkflow,
    TaskIntakeWorkflow,
)


class FakePropertyWorkflow:
    """
    Fake Stage 9 workflow.

    Records every invocation so tests can verify
    precisely when property generation is triggered.
    """

    def __init__(
        self,
    ):
        self.calls = []

    def run(
        self,
        task,
        thread_id=None,
    ):
        self.calls.append(
            {
                "task": task,
                "thread_id": thread_id,
            }
        )

        return PropertyGenerationResult(
            task_id=task.id,
            success=True,
            attempts=1,
        )


class FakeCompleteInterpreter:
    """
    Return a fully specified MonitoringTask
    immediately.
    """

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
                "messages within 5 seconds."
            ),
            protocols=[
                "ngap",
            ],
            requirements=[
                (
                    "Detect more than 10 "
                    "NGAP messages within "
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


class FakeClarifyingInterpreter:
    """
    Initial interpretation is ambiguous.

    Any subsequent explicit clarification makes the
    task complete.
    """

    def interpret(
        self,
        scenario,
    ):
        if not scenario.clarifications:
            task = MonitoringTask(
                id=scenario.id,
                property_id=(
                    scenario.property_id
                ),
                description=(
                    "Detect an abnormal number "
                    "of NGAP messages within a "
                    "limited time window."
                ),
                protocols=[
                    "ngap",
                ],
                requirements=[
                    (
                        "Detect an abnormal number "
                        "of NGAP messages."
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
                    "messages within 5 seconds."
                ),
                protocols=[
                    "ngap",
                ],
                requirements=[
                    (
                        "Detect more than 10 "
                        "NGAP messages."
                    ),
                    (
                        "Evaluate messages within "
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


class FakeAlwaysAmbiguousInterpreter:
    """
    Used to verify the intake-blocked path.
    """

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
                "Ambiguous NGAP monitoring task."
            ),
            protocols=[
                "ngap",
            ],
            ambiguities=[
                (
                    "The threshold remains "
                    "unspecified."
                ),
            ],
        )

        return TaskInterpretationResult(
            scenario_id=scenario.id,
            task=task,
            model="fake/interpreter",
        )


def make_scenario():
    return NaturalLanguageScenario(
        id="nl_integration_001",
        property_id="401",
        text=(
            "Detect an abnormal number of "
            "NGAP messages within a limited "
            "time window."
        ),
    )


def test_complete_task_runs_stage9_once():
    property_workflow = (
        FakePropertyWorkflow()
    )

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                FakeCompleteInterpreter()
            )
        )
    )

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_workflow
            ),
        )
    )

    result = workflow.start(
        scenario=make_scenario(),
        thread_id="nl-complete",
    )

    assert (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .COMPLETED
        )
    )

    assert (
        result.property_result
        is not None
    )

    assert (
        result.property_result.success
        is True
    )

    assert len(
        property_workflow.calls
    ) == 1

    call = (
        property_workflow.calls[0]
    )

    assert (
        call["task"].id
        == "nl_integration_001"
    )

    assert (
        call["thread_id"]
        == "nl-complete:property"
    )


def test_ambiguous_task_does_not_run_stage9():
    property_workflow = (
        FakePropertyWorkflow()
    )

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                FakeClarifyingInterpreter()
            )
        )
    )

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_workflow
            ),
        )
    )

    result = workflow.start(
        scenario=make_scenario(),
        thread_id="nl-interrupt",
    )

    assert (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .CLARIFICATION_REQUIRED
        )
    )

    assert (
        result.clarification_payload
        is not None
    )

    assert (
        len(
            result.clarification_payload[
                "ambiguities"
            ]
        )
        == 2
    )

    assert property_workflow.calls == []


def test_resume_after_clarification_runs_stage9_once():
    property_workflow = (
        FakePropertyWorkflow()
    )

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                FakeClarifyingInterpreter()
            )
        )
    )

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_workflow
            ),
        )
    )

    thread_id = "nl-resume"

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert (
        first.status
        == (
            NaturalLanguageWorkflowStatus
            .CLARIFICATION_REQUIRED
        )
    )

    assert property_workflow.calls == []

    result = workflow.resume(
        clarification={
            "action": "clarify",
            "text": (
                "Use more than 10 messages "
                "within 5 seconds."
            ),
        },
        thread_id=thread_id,
    )

    assert (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .COMPLETED
        )
    )

    assert (
        result.task.ambiguities
        == []
    )

    assert (
        result.metadata[
            "clarification_round"
        ]
        == 1
    )

    assert len(
        property_workflow.calls
    ) == 1

    assert (
        property_workflow.calls[
            0
        ]["thread_id"]
        == "nl-resume:property"
    )


def test_cancelled_task_never_runs_stage9():
    property_workflow = (
        FakePropertyWorkflow()
    )

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                FakeClarifyingInterpreter()
            )
        )
    )

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_workflow
            ),
        )
    )

    thread_id = "nl-cancel"

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert (
        first.status
        == (
            NaturalLanguageWorkflowStatus
            .CLARIFICATION_REQUIRED
        )
    )

    result = workflow.resume(
        clarification={
            "action": "cancel",
        },
        thread_id=thread_id,
    )

    assert (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .CANCELLED
        )
    )

    assert (
        result.metadata[
            "terminal_reason"
        ]
        == "clarification_cancelled"
    )

    assert property_workflow.calls == []


def test_blocked_intake_never_runs_stage9():
    property_workflow = (
        FakePropertyWorkflow()
    )

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                FakeAlwaysAmbiguousInterpreter()
            ),
            max_clarification_rounds=1,
        )
    )

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_workflow
            ),
        )
    )

    thread_id = "nl-blocked"

    first = workflow.start(
        scenario=make_scenario(),
        thread_id=thread_id,
    )

    assert (
        first.status
        == (
            NaturalLanguageWorkflowStatus
            .CLARIFICATION_REQUIRED
        )
    )

    result = workflow.resume(
        clarification={
            "action": "clarify",
            "text": (
                "I still do not know "
                "the threshold."
            ),
        },
        thread_id=thread_id,
    )

    assert (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .BLOCKED
        )
    )

    assert (
        result.metadata[
            "terminal_reason"
        ]
        == "clarification_limit_reached"
    )

    assert property_workflow.calls == []

def test_authorized_assumptions_reach_stage9():
    class AssumptionInterpreter:

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
                    "Example assumed task."
                ),
                protocols=[
                    "ngap",
                ],
                requirements=[
                    "Detect repeated requests.",
                ],
                assumptions=[
                    (
                        "Use a 5-second "
                        "monitoring window."
                    ),
                ],
                ambiguities=[],
            )

            return TaskInterpretationResult(
                scenario_id=scenario.id,
                task=task,
                model="fake/interpreter",
            )

    property_workflow = (
        FakePropertyWorkflow()
    )

    intake_workflow = (
        TaskIntakeWorkflow(
            task_interpreter=(
                AssumptionInterpreter()
            )
        )
    )

    workflow = (
        NaturalLanguagePropertyWorkflow(
            intake_workflow=(
                intake_workflow
            ),
            property_workflow=(
                property_workflow
            ),
        )
    )

    result = workflow.start(
        scenario=make_scenario(),
        thread_id="nl-assumption",
    )

    assert (
        result.status
        == (
            NaturalLanguageWorkflowStatus
            .COMPLETED
        )
    )

    stage9_task = (
        property_workflow.calls[
            0
        ]["task"]
    )

    assert (
        stage9_task.assumptions
        == [
            (
                "Use a 5-second "
                "monitoring window."
            )
        ]
    )

    assert (
        result.metadata[
            "assumption_count"
        ]
        == 1
    )