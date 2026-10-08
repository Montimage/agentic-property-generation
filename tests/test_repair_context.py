from property_agent.context import (
    RepairContextBuilder,
)

from property_agent.models import (
    MonitoringTask,
)


def test_build_repair_context():
    task = MonitoringTask(
        id="repair_context_test",
        property_id="401",
        description="Repair an NGAP property.",
        protocols=["ngap"],
    )

    context = (
        RepairContextBuilder()
        .build(task)
    )

    assert (
        "MMT Property Repair Skill"
        in context.repair_skill
    )

    assert (
        "ngap"
        in context.protocol_attributes
    )

    assert (
        context.protocol_attributes[
            "ngap"
        ]["protocol_id"]
        == 903
    )

    assert (
        "MMT Event-Based Property Format"
        in context.property_format
    )