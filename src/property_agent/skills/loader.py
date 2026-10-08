from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent

def load_skill(skill_name: str) -> str:
    """Load the main SKILL.md document for a skill."""

    skill_path = SKILLS_ROOT / skill_name / "SKILL.md"

    if not skill_path.exists():
        raise FileNotFoundError(
            f"Skill '{skill_name}' was not found at {skill_path}"
        )

    return skill_path.read_text(encoding="utf-8")


def load_skill_resource(
    skill_name: str,
    resource_name: str,
) -> str:
    """Load a supporting resource associated with a skill."""

    resource_path = SKILLS_ROOT / skill_name / resource_name

    if not resource_path.exists():
        raise FileNotFoundError(
            f"Resource '{resource_name}' was not found "
            f"for skill '{skill_name}'."
        )

    return resource_path.read_text(encoding="utf-8")