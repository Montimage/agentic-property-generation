import json
from pathlib import Path

from property_agent.models import (
    AssessmentStatistics,
    CompilationResult,
    CompilationStatus,
    FinalAssessmentStatus,
    FinalPropertyAssessment,
    PropertyGenerationResult,
    GeneratedProperty,
    MonitoringTask,
    ValidationIssue,
    ValidationResult,
)


def test_monitoring_task_from_json():
    """
    Verify that a MonitoringTask can be loaded from
    a scenario JSON file.
    """

    scenario_path = Path(
        "data/scenarios/ngap_example.json"
    )

    data = json.loads(
        scenario_path.read_text(
            encoding="utf-8"
        )
    )

    task = MonitoringTask.model_validate(
        data
    )

    assert task.id == "ngap_example_001"
    assert task.property_id == "101"

    assert "NGAP" in task.protocols

    assert task.monitoring_point == "AMF"


def test_generated_property():
    """
    Verify the default values and basic fields of a
    GeneratedProperty.
    """

    prop = GeneratedProperty(
        task_id="ngap_example_001",
        xml="<property></property>",
        model="test-model",
        metadata={
            "property_id": "101"
        },
    )

    assert prop.task_id == "ngap_example_001"

    assert prop.attempt == 1

    assert prop.xml == "<property></property>"

    assert prop.model == "test-model"

    assert (
        prop.metadata["property_id"]
        == "101"
    )


def test_validation_result():
    """
    Verify the ValidationResult and ValidationIssue
    models.
    """

    result = ValidationResult(
        validator="mmt_syntax",
        valid=False,
        issues=[
            ValidationIssue(
                code="INVALID_ELEMENT",
                message=(
                    "Unexpected XML element."
                ),
                line=10,
            )
        ],
    )

    assert result.valid is False

    assert result.validator == "mmt_syntax"

    assert len(result.issues) == 1

    assert (
        result.issues[0].code
        == "INVALID_ELEMENT"
    )

    assert result.issues[0].line == 10

def test_property_generation_result_stage7():
    generated = GeneratedProperty(
        task_id="task_001",
        xml="<beginning></beginning>",
        model="test/model",
        attempt=2,
    )

    compilation = CompilationResult(
        status=CompilationStatus.COMPILED,
        compile_ok=True,
        returncode=0,
        local_xml_sha256="abc",
        remote_xml_sha256="abc",
        hash_matches=True,
    )

    assessment = FinalPropertyAssessment(
        task_id="task_001",
        property_id="101",
        status=(
            FinalAssessmentStatus.ACCEPTED
        ),
        xml_valid=True,
        syntax_valid=True,
        static_valid=True,
        semantic_valid=True,
        semantic_score=1.0,
        compilation=compilation,
        statistics=AssessmentStatistics(
            final_attempt=2,
            repair_performed=True,
        ),
    )

    result = PropertyGenerationResult(
        task_id="task_001",
        success=True,
        property=generated,
        compilation_validation=(
            compilation
        ),
        final_assessment=assessment,
        attempts=2,
    )

    assert result.success is True

    assert (
        result.compilation_validation.status
        == CompilationStatus.COMPILED
    )

    assert (
        result.final_assessment.status
        == FinalAssessmentStatus.ACCEPTED
    )

def test_monitoring_task_ambiguities_default_empty():
    task = MonitoringTask(
        id="test_task",
        property_id="1001",
        description="Test monitoring task.",
        protocols=["ngap"],
    )

    assert task.ambiguities == []

def test_monitoring_task_preserves_ambiguities():
    task = MonitoringTask(
        id="ambiguous_task",
        property_id="1002",
        description=(
            "Detect an abnormal number of events "
            "within a limited time window."
        ),
        protocols=["ngap"],
        ambiguities=[
            (
                "The numerical threshold is "
                "not specified."
            ),
            (
                "The time-window duration is "
                "not specified."
            ),
        ],
    )

    assert len(
        task.ambiguities
    ) == 2

    assert (
        "threshold"
        in task.ambiguities[0]
    )

    assert (
        "duration"
        in task.ambiguities[1]
    )