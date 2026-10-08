import re
from pathlib import Path

from property_agent.models import (
    FinalPropertyAssessment,
    GeneratedProperty,
)


def _safe_directory_name(
    value: str,
) -> str:
    """
    Convert an identifier into a filesystem-safe
    directory name.
    """

    value = value.strip()

    value = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    )

    return value or "unknown_task"


def save_final_assessment(
    *,
    assessment: FinalPropertyAssessment,
    generated_property: GeneratedProperty,
    output_root: str | Path = "results",
) -> dict[str, Path]:
    """
    Persist the final property and its assessment.

    Creates:

        results/<task_id>/
            final_property.xml
            final_assessment.json

    The property XML is written without modifying its
    contents.
    """

    output_root = Path(
        output_root
    )

    task_directory = (
        output_root
        / _safe_directory_name(
            assessment.task_id
        )
    )

    task_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    property_path = (
        task_directory
        / "final_property.xml"
    )

    assessment_path = (
        task_directory
        / "final_assessment.json"
    )

    property_path.write_text(
        generated_property.xml,
        encoding="utf-8",
    )

    assessment_path.write_text(
        assessment.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    return {
        "property":
            property_path,
        "assessment":
            assessment_path,
    }