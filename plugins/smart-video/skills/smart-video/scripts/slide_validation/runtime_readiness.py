"""Direct loopback readiness challenge for the installed Smart Video runtime."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import secrets
from typing import Any
from urllib import error, parse, request

from .shared import fail, parse_json_text, strict_object


ATTESTATION_PATH = "/api/v1/runtime-readiness/attest"
MAX_RESPONSE_BYTES = 256 * 1024
REQUIRED_CAPABILITIES = (
    "html_author_route",
    "echarts_author_route",
    "trusted_runtime_identity",
)
REQUIRED_ROUTES = {
    "html_author_route": "PATCH /api/v1/video-studio/projects/{project_id}/shots/{shot_id}/html-author",
    "echarts_author_route": "PATCH /api/v1/video-studio/projects/{project_id}/shots/{shot_id}/echarts-author",
}
TRUSTED_RUNTIME_IDENTITY_PATH = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "runtime"
    / "trusted-runtime-identity.v1.json"
)
RUNTIME_BOM_PATH = Path(__file__).resolve().parents[4] / "runtime-bom.json"
_NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
_RESPONSE_FIELDS = {
    "schema_id",
    "version",
    "challenge_nonce",
    "runtime_version",
    "capabilities",
    "routes",
    "runtime_identity",
    "trusted_runtime_identity_bytes_sha256",
    "runtime_inventory_sha256",
}


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def expected_runtime_version() -> str:
    try:
        bom = json.loads(RUNTIME_BOM_PATH.read_text(encoding="utf-8"))
        version = bom["packages"]["@joggai/smartvideo-runtime"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        fail(f"Smart Video runtime BOM is missing or invalid: {exc}")
    if not isinstance(version, str) or not version.strip():
        fail("Smart Video runtime BOM does not pin @joggai/smartvideo-runtime")
    return version.strip()


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        fail(f"runtime readiness value is not canonical JSON: {exc}")


def runtime_inventory_sha256(identity: Any) -> str:
    if not isinstance(identity, dict) or not isinstance(identity.get("files"), dict):
        fail("runtime readiness identity files are invalid")
    files = identity["files"]
    if not files or any(
        not isinstance(path, str)
        or not path
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        for path, digest in files.items()
    ):
        fail("runtime readiness identity inventory is invalid")
    return hashlib.sha256(_canonical_bytes(files)).hexdigest()


def _trusted_identity() -> tuple[dict[str, Any], bytes]:
    try:
        payload = TRUSTED_RUNTIME_IDENTITY_PATH.read_bytes()
        value = parse_json_text(payload.decode("utf-8"), "trusted runtime identity")
    except OSError as exc:
        fail(f"trusted runtime identity is unavailable: {exc}")
    if not isinstance(value, dict):
        fail("trusted runtime identity must be an object")
    return value, payload


def validate_runtime_response(value: Any, challenge_nonce: str) -> dict[str, Any]:
    if _NONCE_RE.fullmatch(challenge_nonce) is None:
        fail("runtime readiness challenge nonce is invalid")
    report = strict_object(value, "runtime readiness response", _RESPONSE_FIELDS)
    if report["schema_id"] != "smart-video.runtime-readiness-attestation.v1" or report["version"] != 1:
        fail("runtime readiness response schema/version is invalid")
    if report["challenge_nonce"] != challenge_nonce:
        fail("runtime readiness response nonce does not match the fresh challenge")
    expected_version = expected_runtime_version()
    if report["runtime_version"] != expected_version:
        fail(
            "runtime readiness response version is not approved: "
            f"expected {expected_version}, got {report['runtime_version']}"
        )
    if report["capabilities"] != list(REQUIRED_CAPABILITIES):
        fail("runtime readiness capabilities do not match the approved contract")
    if report["routes"] != REQUIRED_ROUTES:
        fail("runtime readiness routes do not match the approved contract")
    identity, identity_bytes = _trusted_identity()
    if report["runtime_identity"] != identity:
        fail("runtime readiness identity does not match the Skill-pinned identity")
    expected_identity_sha256 = hashlib.sha256(identity_bytes).hexdigest()
    if report["trusted_runtime_identity_bytes_sha256"] != expected_identity_sha256:
        fail("runtime readiness identity bytes SHA-256 does not match")
    if report["runtime_inventory_sha256"] != runtime_inventory_sha256(identity):
        fail("runtime readiness measured inventory SHA-256 does not match")
    return report


def _loopback_origin(value: str) -> str:
    try:
        parsed = parse.urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        fail(f"runtime readiness requires a valid loopback HTTP origin: {exc}")
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        fail("runtime readiness requires an explicit loopback HTTP origin")
    host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
    return f"http://{host}:{port}"


def attest_runtime(runtime_origin: str) -> dict[str, Any]:
    origin = _loopback_origin(runtime_origin)
    challenge_nonce = secrets.token_hex(32)
    payload = _canonical_bytes({"challenge_nonce": challenge_nonce})
    http_request = request.Request(
        f"{origin}{ATTESTATION_PATH}",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    opener = request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(http_request, timeout=5) as response:
            if response.status != 200:
                fail(f"runtime readiness endpoint returned HTTP {response.status}")
            media_type = response.headers.get_content_type()
            if media_type != "application/json":
                fail("runtime readiness endpoint did not return application/json")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except error.HTTPError as exc:
        fail(f"runtime readiness endpoint returned HTTP {exc.code}")
    except (error.URLError, OSError, TimeoutError) as exc:
        fail(f"runtime readiness endpoint is unavailable: {exc}")
    if len(raw) > MAX_RESPONSE_BYTES:
        fail("runtime readiness response exceeds the size limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        fail(f"runtime readiness response is not UTF-8: {exc}")
    return validate_runtime_response(
        parse_json_text(text, "runtime readiness response"),
        challenge_nonce,
    )
