import json

from property_agent.models import (
    GeneratedProperty,
)

from property_agent.storage import (
    save_generated_property,
)


def test_save_generated_property(
    tmp_path,
):
    generated = GeneratedProperty(
        task_id="task_001",
        xml=(
            "<beginning>"
            "<property "
            'property_id="501" '
            'type_property="SECURITY" '
            'description="Test" />'
            "</beginning>"
        ),
        model="fake/model",
        attempt=1,
        metadata={
            "property_id": "501",
            "retrieval": {
                "enabled": True,
                "used": True,
                "example_ids": [
                    "91"
                ],
            },
        },
    )

    paths = save_generated_property(
        generated_property=generated,
        output_root=tmp_path,
    )

    assert paths["xml"].exists()

    assert (
        paths["metadata"].exists()
    )

    data = json.loads(
        paths[
            "metadata"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        data["task_id"]
        == "task_001"
    )

    assert (
        data["metadata"][
            "retrieval"
        ]["example_ids"]
        == ["91"]
    )