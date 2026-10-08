from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CompilationStatus(str, Enum):
    """
    Outcome of remote MMT property compilation.
    """

    COMPILED = "compiled"

    COMPILATION_FAILED = "compilation_failed"

    REQUEST_INVALID = "request_invalid"

    TIMEOUT = "compilation_timeout"

    ENDPOINT_ERROR = "endpoint_error"

    INVALID_RESPONSE = "invalid_response"


class CompilationResult(BaseModel):
    """
    Result returned after attempting to compile an MMT
    property using the remote MMT compilation endpoint.
    """

    status: CompilationStatus

    attempted: bool = True

    compile_ok: bool | None = None

    request_id: str | None = None

    returncode: int | None = None

    message: str = ""

    stdout: str = ""

    stderr: str = ""

    remote_duration_ms: int | None = None

    client_duration_ms: int | None = None

    size_bytes: int | None = None

    local_xml_sha256: str

    remote_xml_sha256: str | None = None

    hash_matches: bool | None = None

    compiled_artifact_created: bool | None = None

    cleanup_enabled: bool | None = None

    artifacts_deleted: bool | None = None

    cleanup_errors: list[str] = Field(
        default_factory=list
    )

    http_status: int | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )