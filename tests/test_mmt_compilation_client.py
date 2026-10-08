import hashlib
import json

import httpx

from property_agent.models import (
    CompilationStatus,
)

from property_agent.tools import (
    MMTCompilationClient,
    MMTCompilationConfig,
)


XML = """
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


def make_client(
    handler,
):
    transport = httpx.MockTransport(
        handler
    )

    http_client = httpx.Client(
        transport=transport
    )

    return MMTCompilationClient(
        config=MMTCompilationConfig(
            base_url="http://mmt.test"
        ),
        http_client=http_client,
    )


def test_successful_compilation():
    expected_hash = hashlib.sha256(
        XML.encode("utf-8")
    ).hexdigest()

    def handler(
        request: httpx.Request,
    ):
        assert (
            request.content
            == XML.encode("utf-8")
        )

        return httpx.Response(
            status_code=200,
            json={
                "request_id": "abc123",
                "status": "compiled",
                "compile_ok": True,
                "returncode": 0,
                "message": (
                    "MMT property compiled "
                    "successfully."
                ),
                "stdout": "",
                "stderr": "",
                "duration_ms": 125,
                "size_bytes": len(
                    XML.encode("utf-8")
                ),
                "xml_sha256":
                    expected_hash,
                "compiled_artifact_created":
                    True,
                "cleanup_enabled":
                    True,
                "artifacts_deleted":
                    True,
                "cleanup_errors": [],
            },
        )

    client = make_client(
        handler
    )

    result = client.compile_xml(
        XML,
        filename="property_101.xml",
    )

    assert (
        result.status
        == CompilationStatus.COMPILED
    )

    assert result.compile_ok is True
    assert result.returncode == 0
    assert result.hash_matches is True

    assert (
        result.artifacts_deleted
        is True
    )


def test_compilation_failure():
    expected_hash = hashlib.sha256(
        XML.encode("utf-8")
    ).hexdigest()

    def handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            status_code=422,
            json={
                "request_id": "failed123",
                "status":
                    "compilation_failed",
                "compile_ok":
                    False,
                "returncode":
                    1,
                "message":
                    "MMT rejected the property.",
                "stdout":
                    "",
                "stderr":
                    "Compilation error",
                "duration_ms":
                    80,
                "size_bytes":
                    len(
                        XML.encode("utf-8")
                    ),
                "xml_sha256":
                    expected_hash,
                "compiled_artifact_created":
                    False,
                "cleanup_enabled":
                    True,
                "artifacts_deleted":
                    True,
                "cleanup_errors":
                    [],
            },
        )

    client = make_client(
        handler
    )

    result = client.compile_xml(
        XML
    )

    assert (
        result.status
        == CompilationStatus.COMPILATION_FAILED
    )

    assert result.compile_ok is False
    assert result.returncode == 1
    assert result.hash_matches is True


def test_hash_mismatch_is_invalid_response():
    def handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            status_code=200,
            json={
                "request_id": "abc123",
                "status": "compiled",
                "compile_ok": True,
                "returncode": 0,
                "message": "Compiled.",
                "stdout": "",
                "stderr": "",
                "duration_ms": 50,
                "size_bytes": 100,
                "xml_sha256":
                    "incorrect_hash",
                "cleanup_enabled": True,
                "artifacts_deleted": True,
                "cleanup_errors": [],
            },
        )

    client = make_client(
        handler
    )

    result = client.compile_xml(
        XML
    )

    assert (
        result.status
        == CompilationStatus.INVALID_RESPONSE
    )

    assert result.hash_matches is False
    assert result.compile_ok is None


def test_endpoint_error():
    def handler(
        request: httpx.Request,
    ):
        raise httpx.ConnectError(
            "Connection refused",
            request=request,
        )

    client = make_client(
        handler
    )

    result = client.compile_xml(
        XML
    )

    assert (
        result.status
        == CompilationStatus.ENDPOINT_ERROR
    )

    assert result.compile_ok is None