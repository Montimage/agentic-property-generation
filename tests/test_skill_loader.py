import pytest

from property_agent.skills import (
    load_skill,
    load_skill_resource,
)


def test_load_property_generation_skill():
    skill = load_skill("property_generation")

    assert "MMT Property Generation Skill" in skill


def test_load_semantic_validation_skill():
    skill = load_skill("semantic_validation")

    assert "Semantic Validation Skill" in skill


def test_load_property_format():
    content = load_skill_resource(
        "property_generation",
        "property_format.md",
    )

    assert "MMT Event-Based Property Format" in content


def test_unknown_skill():
    with pytest.raises(FileNotFoundError):
        load_skill("unknown_skill")