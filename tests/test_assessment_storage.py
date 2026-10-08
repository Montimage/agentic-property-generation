import json

from property_agent.assessment import (
    save_final_assessment,
)

from property_agent.models import (
    AssessmentStatistics,
    FinalAssessmentStatus,
    FinalPropertyAssessment,
    GeneratedProperty,
)


def test_save_final_assessment(
    tmp_path,
):
    xml = """
<beginning>
    <property
        value="COMPUTE"
        property_id="101"
        description="Test"
        type_property="SECURITY">

        <event
            value="COMPUTE"
            event_id="1"
            description="Test event"
            boolean_expression="ngap.procedure_code == 5"/>

    </property>
</beginning>
""".strip()

    generated_property = GeneratedProperty(
        task_id="storage_test",
        xml=xml,
        model="fake/model",
        attempt=2,
    )

    assessment = FinalPropertyAssessment(
        task_id="storage_test",
        property_id="101",
        status=(
            FinalAssessmentStatus.ACCEPTED
        ),
        xml_valid=True,
        syntax_valid=True,
        static_valid=True,
        semantic_valid=True,
        semantic_score=1.0,
        statistics=AssessmentStatistics(
            final_attempt=2,
            repair_performed=True,
        ),
        reasons=[],
    )

    paths = save_final_assessment(
        assessment=assessment,
        generated_property=generated_property,
        output_root=tmp_path,
    )

    assert (
        paths["property"].exists()
    )

    assert (
        paths["assessment"].exists()
    )

    assert (
        paths["property"].read_text(
            encoding="utf-8"
        )
        == xml
    )

    data = json.loads(
        paths["assessment"].read_text(
            encoding="utf-8"
        )
    )

    assert (
        data["task_id"]
        == "storage_test"
    )

    assert (
        data["property_id"]
        == "101"
    )

    assert (
        data["status"]
        == "accepted"
    )

    assert (
        data["statistics"][
            "final_attempt"
        ]
        == 2
    )