from types import SimpleNamespace

import pytest

from property_agent.agents import (
    PropertyRepairError,
    PropertyRepairer,
)

from property_agent.llm import (
    LLMResponse,
)

from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    RepairDiagnosis,
    RepairDiagnosisStatus,
    RepairIssue,
    RepairIssueSource,
    RepairOutcomeStatus,
)


class FakeRepairLLMClient:
    """
    Fake repair model.

    No Ollama or external API request is performed.
    """

    def __init__(
        self,
        property_id: str = "101",
    ):
        self.config = SimpleNamespace(
            model="fake/repair-model"
        )

        self.property_id = property_id

        self.received_messages = None

        self.call_count = 0

    def complete(
        self,
        messages,
    ):
        self.call_count += 1

        self.received_messages = messages

        return LLMResponse(
            content=f"""
<beginning>

    <property
        value="THEN"
        property_id="{self.property_id}"
        description="Example repaired property"
        type_property="SECURITY">

        <event
            value="COMPUTE"
            event_id="1"
            description="First event"
            boolean_expression="ngap.procedure_code == 5"/>

        <event
            value="COMPUTE"
            event_id="2"
            description="Second event"
            boolean_expression="ngap.amf_ue_id == ngap.amf_ue_id.1"/>

    </property>

</beginning>
""",
            model="fake-provider-model",
            usage={
                "prompt_tokens": 700,
                "completion_tokens": 180,
            },
        )


def make_task():
    return MonitoringTask(
        id="repair_test",
        property_id="101",
        description=(
            "Detect two related NGAP events "
            "within the required sequence."
        ),
        protocols=["ngap"],
    )


def make_current_property():
    return GeneratedProperty(
        task_id="repair_test",
        xml="""
<beginning>

    <property
        property_id="101"
        description="Example"
        type_property="SECURITY">

        <event
            value="COMPUTE"
            event_id="1"
            description="First event"
            boolean_expression="ngap.procedure_code == 5"/>

        <event
            value="COMPUTE"
            event_id="2"
            description="Second event"
            boolean_expression="ngap.amf_ue_id == ngap.amf_ue_id.1"/>

    </property>

</beginning>
""",
        model="fake/generator-model",
        attempt=1,
    )


def make_repairable_diagnosis():
    return RepairDiagnosis(
        status=(
            RepairDiagnosisStatus.REPAIRABLE
        ),
        issues=[
            RepairIssue(
                source=(
                    RepairIssueSource.MMT_SYNTAX
                ),
                code=(
                    "INVALID_COMPUTE_EVENT_COUNT"
                ),
                message=(
                    "The property defaults to "
                    "COMPUTE but contains multiple "
                    "events."
                ),
                evidence=None,
                repairable=True,
                blocking=False,
            )
        ],
        blocking_reasons=[],
        summary=(
            "The property structure can "
            "be repaired."
        ),
    )


def test_repair_property():
    client = FakeRepairLLMClient(
        property_id="101"
    )

    repairer = PropertyRepairer(
        client=client
    )

    result = repairer.repair(
        task=make_task(),
        current_property=(
            make_current_property()
        ),
        diagnosis=(
            make_repairable_diagnosis()
        ),
    )

    assert (
        result.status
        == RepairOutcomeStatus.REPAIRED
    )

    assert (
        result.repaired_property
        is not None
    )

    assert (
        result.repaired_property.attempt
        == 2
    )

    assert (
        'property_id="101"'
        in result.repaired_property.xml
    )

    assert (
        'value="THEN"'
        in result.repaired_property.xml
    )

    assert (
        result.repaired_property.metadata[
            "repair_of_attempt"
        ]
        == 1
    )

    assert (
        "INVALID_COMPUTE_EVENT_COUNT"
        in result.repaired_property.metadata[
            "repair_issue_codes"
        ]
    )


def test_repairer_receives_diagnosis():
    client = FakeRepairLLMClient()

    repairer = PropertyRepairer(
        client=client
    )

    repairer.repair(
        task=make_task(),
        current_property=(
            make_current_property()
        ),
        diagnosis=(
            make_repairable_diagnosis()
        ),
    )

    user_message = (
        client.received_messages[1][
            "content"
        ]
    )

    assert (
        "INVALID_COMPUTE_EVENT_COUNT"
        in user_message
    )

    assert (
        "Repair only the issues "
        "identified by the structured diagnosis"
        in user_message
    )

def test_repairer_exposes_security_c_type_without_dpi_metadata():
    """
    Verify that the repair model receives the
    embedded-function C type for protocol attributes
    without unnecessary internal DPI metadata.
    """
    client = FakeRepairLLMClient()

    repairer = PropertyRepairer(
        client=client
    )

    repairer.repair(
        task=make_task(),
        current_property=(
            make_current_property()
        ),
        diagnosis=(
            make_repairable_diagnosis()
        ),
    )

    user_message = (
        client.received_messages[
            1
        ]["content"]
    )

    assert (
        '"qualified_name": "ngap.amf_ue_id"'
        in user_message
    )

    assert (
        '"security_c_type": "double"'
        in user_message
    )

    assert (
        '"qualified_name": "ngap.p_payload"'
        in user_message
    )

    assert (
        '"security_c_type": null'
        in user_message
    )

    assert (
        '"dpi_type"'
        not in user_message
    )

    assert (
        '"data_len"'
        not in user_message
    )

def test_repairer_instructs_use_of_security_c_type():
    """
    Verify that embedded-function repair is grounded
    in the supplied Security C type metadata.
    """
    client = FakeRepairLLMClient()

    repairer = PropertyRepairer(
        client=client
    )

    repairer.repair(
        task=make_task(),
        current_property=(
            make_current_property()
        ),
        diagnosis=(
            make_repairable_diagnosis()
        ),
    )

    system_message = (
        client.received_messages[
            0
        ]["content"]
    )

    assert (
        "security_c_type"
        in system_message
    )

    assert (
        "do not replace a known "
        "`security_c_type` with a generic pointer type"
        in system_message
    )

def test_blocked_repair_does_not_call_llm():
    client = FakeRepairLLMClient()

    diagnosis = RepairDiagnosis(
        status=RepairDiagnosisStatus.BLOCKED,
        issues=[
            RepairIssue(
                source=(
                    RepairIssueSource.SEMANTIC
                ),
                code="TASK_UNDERSPECIFIED",
                message=(
                    "The task does not define "
                    "the required threshold."
                ),
                evidence=None,
                repairable=False,
                blocking=True,
            )
        ],
        blocking_reasons=[
            (
                "The task does not define "
                "the required threshold."
            )
        ],
        summary=(
            "Automatic repair is blocked."
        ),
    )

    repairer = PropertyRepairer(
        client=client
    )

    result = repairer.repair(
        task=make_task(),
        current_property=(
            make_current_property()
        ),
        diagnosis=diagnosis,
    )

    assert (
        result.status
        == RepairOutcomeStatus.BLOCKED
    )

    assert (
        result.repaired_property
        is None
    )

    assert client.call_count == 0


def test_repair_rejects_changed_property_id():
    client = FakeRepairLLMClient(
        property_id="999"
    )

    repairer = PropertyRepairer(
        client=client
    )

    with pytest.raises(
        PropertyRepairError,
        match="property_id",
    ):
        repairer.repair(
            task=make_task(),
            current_property=(
                make_current_property()
            ),
            diagnosis=(
                make_repairable_diagnosis()
            ),
        )