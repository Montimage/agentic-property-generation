import re
from pathlib import Path

from property_agent.models import (
    GeneratedProperty,
)


def _safe_name(
    value: str,
) -> str:
    value = value.strip()

    value = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    )

    return value or "unknown"


def save_generated_property(
    generated_property: GeneratedProperty,
    output_root: str | Path = "results",
) -> dict[str, Path]:
    """
    Persist one generated property attempt and its
    metadata.

    Stored results are experimental artifacts only.

    They are not added to the verified-example
    repository and are therefore not eligible for
    retrieval.
    """

    output_root = Path(
        output_root
    )

    task_directory = (
        output_root
        / _safe_name(
            generated_property.task_id
        )
    )

    task_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stem = (
        f"generation_attempt_"
        f"{generated_property.attempt}"
    )

    xml_path = (
        task_directory
        / f"{stem}.xml"
    )

    metadata_path = (
        task_directory
        / f"{stem}.json"
    )

    xml_path.write_text(
        generated_property.xml,
        encoding="utf-8",
    )

    metadata_path.write_text(
        generated_property.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    return {
        "xml": xml_path,
        "metadata":
            metadata_path,
    }