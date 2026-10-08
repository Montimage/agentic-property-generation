import hashlib
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from property_agent.models import (
    CompilationResult,
    CompilationStatus,
    GeneratedProperty,
)


class MMTCompilationConfig(BaseModel):
    """
    Configuration for the remote MMT compilation
    endpoint.
    """

    base_url: str

    compile_path: str = "/compile"

    health_path: str = "/health"

    timeout_seconds: float = Field(
        default=200.0,
        gt=0,
    )


class MMTCompilationClient:
    """
    Client for the remote MMT-Security compilation
    validation endpoint.

    The client sends the exact XML candidate and records
    the compilation evidence returned by the real MMT
    compile_rule executable.
    """

    def __init__(
        self,
        config: MMTCompilationConfig,
        http_client: httpx.Client | None = None,
    ):
        self.config = config

        self.http_client = http_client

    def _url(
        self,
        path: str,
    ) -> str:
        return (
            self.config.base_url.rstrip("/")
            + "/"
            + path.lstrip("/")
        )

    def check_health(
        self,
    ) -> dict[str, Any]:
        """
        Check availability of the remote compilation
        environment.
        """

        url = self._url(
            self.config.health_path
        )

        try:
            if self.http_client is not None:
                response = self.http_client.get(
                    url,
                    timeout=10.0,
                )
            else:
                response = httpx.get(
                    url,
                    timeout=10.0,
                )

            response.raise_for_status()

            data = response.json()

            if not isinstance(
                data,
                dict,
            ):
                raise ValueError(
                    "Health endpoint did not "
                    "return a JSON object."
                )

            return data

        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

    def compile_property(
        self,
        generated_property: GeneratedProperty,
    ) -> CompilationResult:
        """
        Compile a GeneratedProperty using the remote
        MMT compilation endpoint.
        """

        filename = (
            f"property_"
            f"{generated_property.metadata.get('property_id', 'unknown')}"
            f"_attempt_"
            f"{generated_property.attempt}.xml"
        )

        return self.compile_xml(
            xml=generated_property.xml,
            filename=filename,
        )

    def compile_xml(
        self,
        xml: str,
        filename: str = "rule.xml",
    ) -> CompilationResult:
        """
        Send XML exactly as UTF-8 bytes to the remote
        compiler and convert its response into a
        CompilationResult.
        """

        xml_bytes = xml.encode(
            "utf-8"
        )

        local_hash = hashlib.sha256(
            xml_bytes
        ).hexdigest()

        url = self._url(
            self.config.compile_path
        )

        headers = {
            "Content-Type":
                "application/xml",
            "X-Rule-Filename":
                filename,
        }

        started = time.perf_counter()

        try:
            if self.http_client is not None:
                response = self.http_client.post(
                    url,
                    content=xml_bytes,
                    headers=headers,
                    timeout=(
                        self.config.timeout_seconds
                    ),
                )
            else:
                response = httpx.post(
                    url,
                    content=xml_bytes,
                    headers=headers,
                    timeout=(
                        self.config.timeout_seconds
                    ),
                )

        except httpx.TimeoutException as exc:
            return CompilationResult(
                status=CompilationStatus.TIMEOUT,
                compile_ok=None,
                message=(
                    "The remote MMT compilation "
                    "request timed out."
                ),
                stderr=str(exc),
                client_duration_ms=self._elapsed_ms(
                    started
                ),
                size_bytes=len(xml_bytes),
                local_xml_sha256=local_hash,
            )

        except httpx.RequestError as exc:
            return CompilationResult(
                status=(
                    CompilationStatus.ENDPOINT_ERROR
                ),
                compile_ok=None,
                message=(
                    "The remote MMT compilation "
                    "endpoint could not be reached."
                ),
                stderr=str(exc),
                client_duration_ms=self._elapsed_ms(
                    started
                ),
                size_bytes=len(xml_bytes),
                local_xml_sha256=local_hash,
            )

        client_duration = self._elapsed_ms(
            started
        )

        try:
            data = response.json()

        except ValueError:
            return CompilationResult(
                status=(
                    CompilationStatus.INVALID_RESPONSE
                ),
                compile_ok=None,
                message=(
                    "The compilation endpoint returned "
                    "a non-JSON response."
                ),
                stderr=response.text[-4000:],
                client_duration_ms=client_duration,
                size_bytes=len(xml_bytes),
                local_xml_sha256=local_hash,
                http_status=response.status_code,
            )

        if not isinstance(
            data,
            dict,
        ):
            return CompilationResult(
                status=(
                    CompilationStatus.INVALID_RESPONSE
                ),
                compile_ok=None,
                message=(
                    "The compilation endpoint response "
                    "was not a JSON object."
                ),
                client_duration_ms=client_duration,
                size_bytes=len(xml_bytes),
                local_xml_sha256=local_hash,
                http_status=response.status_code,
            )

        remote_hash = data.get(
            "xml_sha256"
        )

        hash_matches = (
            remote_hash == local_hash
            if remote_hash is not None
            else None
        )

        if hash_matches is False:
            return CompilationResult(
                status=(
                    CompilationStatus.INVALID_RESPONSE
                ),
                compile_ok=None,
                request_id=data.get(
                    "request_id"
                ),
                message=(
                    "The XML hash returned by the "
                    "compilation endpoint does not "
                    "match the property that was sent."
                ),
                stdout=data.get(
                    "stdout",
                    "",
                ),
                stderr=data.get(
                    "stderr",
                    "",
                ),
                remote_duration_ms=data.get(
                    "duration_ms"
                ),
                client_duration_ms=client_duration,
                size_bytes=len(xml_bytes),
                local_xml_sha256=local_hash,
                remote_xml_sha256=remote_hash,
                hash_matches=False,
                http_status=response.status_code,
                metadata={
                    "remote_status":
                        data.get("status"),
                },
            )

        remote_status = data.get(
            "status"
        )

        try:
            status = CompilationStatus(
                remote_status
            )

        except (
            ValueError,
            TypeError,
        ):
            return CompilationResult(
                status=(
                    CompilationStatus.INVALID_RESPONSE
                ),
                compile_ok=None,
                request_id=data.get(
                    "request_id"
                ),
                message=(
                    "The compilation endpoint returned "
                    "an unknown status."
                ),
                stdout=data.get(
                    "stdout",
                    "",
                ),
                stderr=data.get(
                    "stderr",
                    "",
                ),
                remote_duration_ms=data.get(
                    "duration_ms"
                ),
                client_duration_ms=client_duration,
                size_bytes=len(xml_bytes),
                local_xml_sha256=local_hash,
                remote_xml_sha256=remote_hash,
                hash_matches=hash_matches,
                http_status=response.status_code,
                metadata={
                    "remote_status":
                        remote_status,
                },
            )

        # Verify that status and compile_ok are
        # internally consistent.
        compile_ok = data.get(
            "compile_ok"
        )

        if (
            status == CompilationStatus.COMPILED
            and compile_ok is not True
        ):
            return self._invalid_response(
                data=data,
                response=response,
                local_hash=local_hash,
                remote_hash=remote_hash,
                hash_matches=hash_matches,
                client_duration=client_duration,
                size_bytes=len(xml_bytes),
                message=(
                    "Endpoint returned status "
                    "'compiled' without "
                    "compile_ok=true."
                ),
            )

        if (
            status
            == CompilationStatus.COMPILATION_FAILED
            and compile_ok is not False
        ):
            return self._invalid_response(
                data=data,
                response=response,
                local_hash=local_hash,
                remote_hash=remote_hash,
                hash_matches=hash_matches,
                client_duration=client_duration,
                size_bytes=len(xml_bytes),
                message=(
                    "Endpoint returned status "
                    "'compilation_failed' without "
                    "compile_ok=false."
                ),
            )

        return CompilationResult(
            status=status,
            compile_ok=compile_ok,
            request_id=data.get(
                "request_id"
            ),
            returncode=data.get(
                "returncode"
            ),
            message=data.get(
                "message",
                "",
            ),
            stdout=data.get(
                "stdout",
                "",
            ),
            stderr=data.get(
                "stderr",
                "",
            ),
            remote_duration_ms=data.get(
                "duration_ms"
            ),
            client_duration_ms=client_duration,
            size_bytes=data.get(
                "size_bytes",
                len(xml_bytes),
            ),
            local_xml_sha256=local_hash,
            remote_xml_sha256=remote_hash,
            hash_matches=hash_matches,
            compiled_artifact_created=data.get(
                "compiled_artifact_created"
            ),
            cleanup_enabled=data.get(
                "cleanup_enabled"
            ),
            artifacts_deleted=data.get(
                "artifacts_deleted"
            ),
            cleanup_errors=data.get(
                "cleanup_errors",
                [],
            ),
            http_status=response.status_code,
        )

    @staticmethod
    def _elapsed_ms(
        started: float,
    ) -> int:
        return int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

    @staticmethod
    def _invalid_response(
        *,
        data: dict[str, Any],
        response: httpx.Response,
        local_hash: str,
        remote_hash: str | None,
        hash_matches: bool | None,
        client_duration: int,
        size_bytes: int,
        message: str,
    ) -> CompilationResult:

        return CompilationResult(
            status=(
                CompilationStatus.INVALID_RESPONSE
            ),
            compile_ok=None,
            request_id=data.get(
                "request_id"
            ),
            returncode=data.get(
                "returncode"
            ),
            message=message,
            stdout=data.get(
                "stdout",
                "",
            ),
            stderr=data.get(
                "stderr",
                "",
            ),
            remote_duration_ms=data.get(
                "duration_ms"
            ),
            client_duration_ms=client_duration,
            size_bytes=size_bytes,
            local_xml_sha256=local_hash,
            remote_xml_sha256=remote_hash,
            hash_matches=hash_matches,
            http_status=response.status_code,
        )