from pydantic import BaseModel, Field


class PropertyWorkflowConfig(BaseModel):
    """
    Configuration controlling the autonomous property
    generation workflow.
    """

    max_repair_attempts: int = Field(
        default=2,
        ge=0,
    )

    save_artifacts: bool = True

    results_dir: str = "results"

    recursion_limit: int = Field(
        default=50,
        ge=10,
    )