import hashlib
import os
import re
import subprocess
import time

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ============================================================
# Configuration
# ============================================================

MMT_SECURITY_BIN = Path(
    "/opt/mmt/security/bin"
)

COMPILE_RULE = (
    MMT_SECURITY_BIN
    / "compile_rule"
)

XML_DIR = Path(
    "/opt/mmt/security/rules/custom_xml"
)

SO_DIR = Path(
    "/opt/mmt/security/rules/custom_so"
)

COMPILE_TIMEOUT_SECONDS = 180

MAX_COMPILER_OUTPUT_LENGTH = 4000


# Delete the XML and .so generated during validation after
# every compilation attempt.
#
# Default: True
#
# Can be overridden with:
#
# export MMT_DELETE_ARTIFACTS_AFTER_COMPILE=false
#
DELETE_ARTIFACTS_AFTER_COMPILE = (
    os.getenv(
        "MMT_DELETE_ARTIFACTS_AFTER_COMPILE",
        "true",
    )
    .strip()
    .lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title="MMT-Security Compilation Validator",
    version="0.2",
)


# ============================================================
# Utility functions
# ============================================================

def sanitize_name(
    name: str,
) -> str:
    """
    Sanitize the filename received through the
    X-Rule-Filename header.
    """

    name = (
        name
        .strip()
        .replace(" ", "_")
    )

    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name,
    )

    return name[:80]


def run_cmd(
    cmd: list[str],
    timeout: int = COMPILE_TIMEOUT_SECONDS,
) -> tuple[int, str, str]:
    """
    Execute the real MMT compile_rule command.

    Returns:
        return code,
        stdout,
        stderr
    """

    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return (
        process.returncode,
        process.stdout,
        process.stderr,
    )


def safe_unlink(
    path: Path,
) -> str | None:
    """
    Best-effort deletion of one artifact.

    Returns None when deletion succeeds or the file
    does not exist.

    Returns an error message when deletion fails.
    """

    try:
        if path.exists():
            path.unlink()

        return None

    except Exception as exc:
        return (
            f"Failed to delete {path}: {exc}"
        )


def cleanup_artifacts(
    paths: list[Path],
) -> list[str]:
    """
    Delete files created during compilation.

    Cleanup only happens when
    DELETE_ARTIFACTS_AFTER_COMPILE is enabled.
    """

    if not DELETE_ARTIFACTS_AFTER_COMPILE:
        return []

    errors = []

    for path in reversed(paths):
        error = safe_unlink(
            path
        )

        if error:
            errors.append(
                error
            )

    return errors


def artifacts_deleted(
    paths: list[Path],
) -> bool:
    """
    Return True when cleanup is enabled and none of
    the compilation artifacts remain on disk.
    """

    if not DELETE_ARTIFACTS_AFTER_COMPILE:
        return False

    return not any(
        path.exists()
        for path in paths
    )


def trim_output(
    text: str | None,
) -> str:
    """
    Limit compiler output stored in the response.
    """

    if not text:
        return ""

    return text[
        -MAX_COMPILER_OUTPUT_LENGTH:
    ]


# ============================================================
# Health endpoint
# ============================================================

@app.get("/health")
def health():
    """
    Verify that the remote MMT compilation environment
    is available.
    """

    compile_rule_exists = (
        COMPILE_RULE.exists()
    )

    xml_dir_exists = (
        XML_DIR.exists()
    )

    so_dir_exists = (
        SO_DIR.exists()
    )

    xml_dir_writable = (
        xml_dir_exists
        and os.access(
            str(XML_DIR),
            os.W_OK,
        )
    )

    so_dir_writable = (
        so_dir_exists
        and os.access(
            str(SO_DIR),
            os.W_OK,
        )
    )

    ok = all(
        [
            compile_rule_exists,
            xml_dir_exists,
            xml_dir_writable,
            so_dir_exists,
            so_dir_writable,
        ]
    )

    return {
        "ok": ok,
        "compile_rule_exists":
            compile_rule_exists,
        "xml_dir_exists":
            xml_dir_exists,
        "xml_dir_writable":
            xml_dir_writable,
        "so_dir_exists":
            so_dir_exists,
        "so_dir_writable":
            so_dir_writable,
        "delete_artifacts_after_compile":
            DELETE_ARTIFACTS_AFTER_COMPILE,
        "compile_timeout_seconds":
            COMPILE_TIMEOUT_SECONDS,
    }


# ============================================================
# Compilation endpoint
# ============================================================

@app.post("/compile")
async def compile_property(
    request: Request,
):
    """
    Receive an MMT XML property and validate it using
    the real MMT compile_rule executable.

    The rule is compiled into a temporary .so file.

    The rule is NOT copied into the active MMT rule
    directory and is NOT deployed.

    By default, both the XML and generated .so are
    deleted after the compilation attempt.
    """

    request_id = uuid4().hex

    started = time.perf_counter()

    raw = await request.body()

    size_bytes = len(raw)

    xml_sha256 = hashlib.sha256(
        raw
    ).hexdigest()

    artifacts: list[Path] = []

    xml_path: Path | None = None
    so_path: Path | None = None

    def duration_ms() -> int:
        return int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

    # --------------------------------------------------------
    # Check MMT environment
    # --------------------------------------------------------

    if not COMPILE_RULE.exists():
        return JSONResponse(
            status_code=500,
            content={
                "request_id":
                    request_id,
                "status":
                    "endpoint_error",
                "compile_ok":
                    None,
                "returncode":
                    None,
                "message":
                    "MMT compile_rule binary is missing.",
                "stdout":
                    "",
                "stderr":
                    str(COMPILE_RULE),
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    True,
                "cleanup_errors":
                    [],
            },
        )

    for directory in (
        XML_DIR,
        SO_DIR,
    ):
        if not directory.exists():
            return JSONResponse(
                status_code=500,
                content={
                    "request_id":
                        request_id,
                    "status":
                        "endpoint_error",
                    "compile_ok":
                        None,
                    "returncode":
                        None,
                    "message":
                        "Required MMT directory "
                        "does not exist.",
                    "stdout":
                        "",
                    "stderr":
                        str(directory),
                    "duration_ms":
                        duration_ms(),
                    "size_bytes":
                        size_bytes,
                    "xml_sha256":
                        xml_sha256,
                    "cleanup_enabled":
                        DELETE_ARTIFACTS_AFTER_COMPILE,
                    "artifacts_deleted":
                        True,
                    "cleanup_errors":
                        [],
                },
            )

        if not os.access(
            str(directory),
            os.W_OK,
        ):
            return JSONResponse(
                status_code=500,
                content={
                    "request_id":
                        request_id,
                    "status":
                        "endpoint_error",
                    "compile_ok":
                        None,
                    "returncode":
                        None,
                    "message":
                        "Required MMT directory "
                        "is not writable.",
                    "stdout":
                        "",
                    "stderr":
                        str(directory),
                    "duration_ms":
                        duration_ms(),
                    "size_bytes":
                        size_bytes,
                    "xml_sha256":
                        xml_sha256,
                    "cleanup_enabled":
                        DELETE_ARTIFACTS_AFTER_COMPILE,
                    "artifacts_deleted":
                        True,
                    "cleanup_errors":
                        [],
                },
            )

    # --------------------------------------------------------
    # Validate request body
    # --------------------------------------------------------

    try:
        xml_text = raw.decode(
            "utf-8"
        )

    except UnicodeDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "request_id":
                    request_id,
                "status":
                    "request_invalid",
                "compile_ok":
                    None,
                "returncode":
                    None,
                "message":
                    "Request body is not valid UTF-8.",
                "stdout":
                    "",
                "stderr":
                    "",
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    True,
                "cleanup_errors":
                    [],
            },
        )

    if (
        len(raw) < 20
        or not xml_text
        .lstrip()
        .startswith("<")
    ):
        return JSONResponse(
            status_code=400,
            content={
                "request_id":
                    request_id,
                "status":
                    "request_invalid",
                "compile_ok":
                    None,
                "returncode":
                    None,
                "message":
                    "Request body does not look like XML.",
                "stdout":
                    "",
                "stderr":
                    "",
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    True,
                "cleanup_errors":
                    [],
            },
        )

    # --------------------------------------------------------
    # Build unique temporary artifact names
    # --------------------------------------------------------

    original_name = (
        request.headers.get(
            "X-Rule-Filename",
            "rule.xml",
        )
    )

    safe_name = sanitize_name(
        original_name
    )

    if not safe_name.lower().endswith(
        ".xml"
    ):
        safe_name += ".xml"

    original_stem = Path(
        safe_name
    ).stem

    unique_stem = (
        f"{original_stem}_{request_id}"
    )

    xml_path = (
        XML_DIR
        / f"{unique_stem}.xml"
    )

    so_path = (
        SO_DIR
        / f"{unique_stem}.so"
    )

    artifacts = [
        xml_path,
        so_path,
    ]

    # --------------------------------------------------------
    # Store exact XML temporarily
    # --------------------------------------------------------

    try:
        # Important:
        # write exactly the bytes received by this endpoint.
        # This makes xml_sha256 correspond exactly to the
        # property compiled by MMT.
        xml_path.write_bytes(
            raw
        )

    except Exception as exc:
        cleanup_errors = (
            cleanup_artifacts(
                artifacts
            )
        )

        return JSONResponse(
            status_code=500,
            content={
                "request_id":
                    request_id,
                "status":
                    "endpoint_error",
                "compile_ok":
                    None,
                "returncode":
                    None,
                "message":
                    "Unable to create temporary "
                    "property file.",
                "stdout":
                    "",
                "stderr":
                    str(exc),
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    artifacts_deleted(
                        artifacts
                    ),
                "cleanup_errors":
                    cleanup_errors,
            },
        )

    # --------------------------------------------------------
    # Actual MMT compilation
    # --------------------------------------------------------

    try:
        returncode, stdout, stderr = run_cmd(
            [
                str(COMPILE_RULE),
                str(so_path),
                str(xml_path),
            ],
            timeout=(
                COMPILE_TIMEOUT_SECONDS
            ),
        )

    except subprocess.TimeoutExpired as exc:
        # compile_rule may have produced a partial .so,
        # so both paths are always considered for cleanup.
        cleanup_errors = (
            cleanup_artifacts(
                artifacts
            )
        )

        return JSONResponse(
            status_code=504,
            content={
                "request_id":
                    request_id,
                "status":
                    "compilation_timeout",
                "compile_ok":
                    None,
                "returncode":
                    None,
                "message":
                    "MMT property compilation timed out.",
                "stdout":
                    trim_output(
                        (
                            exc.stdout.decode(
                                "utf-8",
                                errors="replace",
                            )
                            if isinstance(
                                exc.stdout,
                                bytes,
                            )
                            else exc.stdout
                        )
                    ),
                "stderr":
                    trim_output(
                        (
                            exc.stderr.decode(
                                "utf-8",
                                errors="replace",
                            )
                            if isinstance(
                                exc.stderr,
                                bytes,
                            )
                            else exc.stderr
                        )
                    ),
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    artifacts_deleted(
                        artifacts
                    ),
                "cleanup_errors":
                    cleanup_errors,
            },
        )

    except Exception as exc:
        cleanup_errors = (
            cleanup_artifacts(
                artifacts
            )
        )

        return JSONResponse(
            status_code=500,
            content={
                "request_id":
                    request_id,
                "status":
                    "endpoint_error",
                "compile_ok":
                    None,
                "returncode":
                    None,
                "message":
                    "Failed to execute the MMT compiler.",
                "stdout":
                    "",
                "stderr":
                    str(exc),
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    artifacts_deleted(
                        artifacts
                    ),
                "cleanup_errors":
                    cleanup_errors,
            },
        )

    # --------------------------------------------------------
    # Determine actual compilation result
    # --------------------------------------------------------

    so_created = so_path.exists()

    compile_ok = (
        returncode == 0
        and so_created
    )

    # Preserve compiler evidence before removing the files.
    compiler_stdout = trim_output(
        stdout
    )

    compiler_stderr = trim_output(
        stderr
    )

    cleanup_errors = (
        cleanup_artifacts(
            artifacts
        )
    )

    deleted = artifacts_deleted(
        artifacts
    )

    # --------------------------------------------------------
    # Compilation failure
    # --------------------------------------------------------

    if not compile_ok:

        if (
            returncode == 0
            and not so_created
        ):
            message = (
                "MMT compile_rule returned success "
                "but did not create the expected "
                "compiled .so file."
            )

        else:
            message = (
                "MMT rejected or failed to compile "
                "the property."
            )

        return JSONResponse(
            status_code=422,
            content={
                "request_id":
                    request_id,
                "status":
                    "compilation_failed",
                "compile_ok":
                    False,
                "returncode":
                    returncode,
                "message":
                    message,
                "stdout":
                    compiler_stdout,
                "stderr":
                    compiler_stderr,
                "duration_ms":
                    duration_ms(),
                "size_bytes":
                    size_bytes,
                "xml_sha256":
                    xml_sha256,
                "compiled_artifact_created":
                    so_created,
                "cleanup_enabled":
                    DELETE_ARTIFACTS_AFTER_COMPILE,
                "artifacts_deleted":
                    deleted,
                "cleanup_errors":
                    cleanup_errors,
            },
        )

    # --------------------------------------------------------
    # Compilation succeeded
    # --------------------------------------------------------

    return JSONResponse(
        status_code=200,
        content={
            "request_id":
                request_id,
            "status":
                "compiled",
            "compile_ok":
                True,
            "returncode":
                returncode,
            "message":
                "MMT property compiled successfully.",
            "stdout":
                compiler_stdout,
            "stderr":
                compiler_stderr,
            "duration_ms":
                duration_ms(),
            "size_bytes":
                size_bytes,
            "xml_sha256":
                xml_sha256,
            "compiled_artifact_created":
                True,
            "cleanup_enabled":
                DELETE_ARTIFACTS_AFTER_COMPILE,
            "artifacts_deleted":
                deleted,
            "cleanup_errors":
                cleanup_errors,
        },
    )


# ============================================================
# Debug endpoint
# ============================================================

@app.post("/compile/debug")
async def debug_property(
    request: Request,
):
    """
    Debug-only endpoint.

    Receives the payload but does not compile it.
    """

    raw = await request.body()

    body = raw.decode(
        "utf-8",
        errors="replace",
    )

    xml_sha256 = hashlib.sha256(
        raw
    ).hexdigest()

    print(
        "=== DEBUG PROPERTY RECEIVED ==="
    )

    print("Headers:")

    for key, value in (
        request.headers.items()
    ):
        print(
            f"{key}: {value}"
        )

    print("Body:")
    print(body)

    print(
        "=== END DEBUG PROPERTY ==="
    )

    return {
        "received": True,
        "size_bytes": len(raw),
        "xml_sha256": xml_sha256,
        "message": (
            "Payload received successfully. "
            "No compilation was performed."
        ),
    }