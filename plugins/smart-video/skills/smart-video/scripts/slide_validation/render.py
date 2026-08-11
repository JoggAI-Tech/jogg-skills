"""Artifact-file and bounded post-render evidence validation."""

from __future__ import annotations

import binascii
from pathlib import Path
import struct
from typing import Any
import zlib

from .contracts import *

PNG_MAX_FILE_BYTES = 16 * 1024 * 1024
PNG_MAX_DIMENSION = 8192
PNG_MAX_PIXELS = 20_000_000
PNG_MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024
TRUSTED_RUNTIME_IDENTITY_PATH = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "runtime"
    / "trusted-runtime-identity.v1.json"
)

BROWSER_FAILURE_COUNT_FIELDS = {
    "runtime_exceptions",
    "log_errors",
    "network_load_failures",
    "http_error_responses",
    "console_errors",
}


def validate_successful_browser_failures(value: Any) -> None:
    failures = strict_object(
        value,
        "runtime_attestation.observed_root.browser_failures",
        {"total_count", "detail_limit", "details_truncated", "counts", "details"},
    )
    counts = strict_object(
        failures["counts"],
        "runtime_attestation.observed_root.browser_failures.counts",
        BROWSER_FAILURE_COUNT_FIELDS,
    )
    if (
        type(failures["total_count"]) is not int
        or failures["total_count"] != 0
        or any(type(counts[field]) is not int or counts[field] != 0 for field in BROWSER_FAILURE_COUNT_FIELDS)
    ):
        fail("runtime attestation browser failures must be zero")
    if failures["detail_limit"] != 20:
        fail("runtime attestation browser failure detail limit must be 20")
    if failures["details_truncated"] is not False:
        fail("runtime attestation browser failure details must not be truncated")
    if not isinstance(failures["details"], list) or failures["details"]:
        fail("runtime attestation browser failure details must be empty")


def validate_runtime_attestation(
    value: Any,
    request: dict[str, Any],
    manifest: dict[str, Any],
    screenshot_sha256: str,
) -> None:
    attestation = strict_object(
        value,
        "render_report.runtime_attestation",
        {
            "schema_id", "version", "runtime_identity", "manifest_id",
            "author_sha256", "adapter_sha256", "screenshot_sha256",
            "final_timeline_seconds", "observed_root",
        },
    )
    if attestation["schema_id"] != "smart-video.runtime-attestation.v1" or type(attestation["version"]) is not int or attestation["version"] != 1:
        fail("runtime attestation schema/version must be smart-video.runtime-attestation.v1 version 1")
    approved_identity = load_json(TRUSTED_RUNTIME_IDENTITY_PATH, "trusted runtime identity")
    if attestation["runtime_identity"] != approved_identity:
        fail("runtime identity is not approved")
    if attestation["manifest_id"] != manifest["manifest_id"]:
        fail("runtime attestation manifest identity does not match manifest")
    if require_sha256(attestation["author_sha256"], "runtime_attestation.author_sha256") != manifest["artifacts"]["author"]["sha256"]:
        fail("runtime attestation author SHA-256 does not match manifest")
    if require_sha256(attestation["adapter_sha256"], "runtime_attestation.adapter_sha256") != manifest["artifacts"]["adapter"]["sha256"]:
        fail("runtime attestation adapter SHA-256 does not match manifest")
    if require_sha256(attestation["screenshot_sha256"], "runtime_attestation.screenshot_sha256") != screenshot_sha256:
        fail("runtime attestation screenshot SHA-256 does not match rendered PNG")
    final_seconds = require_number(attestation["final_timeline_seconds"], "runtime_attestation.final_timeline_seconds")
    if not math.isclose(final_seconds, float(manifest["duration_seconds"]), abs_tol=1e-9):
        fail("runtime attestation final timeline time does not match manifest duration")
    observed = strict_object(
        attestation["observed_root"],
        "runtime_attestation.observed_root",
        {
            "design_strategy", "design_version", "manifest_id", "render_mode",
            "author_spec_sha256", "adapter_state", "final_action", "canvas_pixels",
            "echarts_text_count", "echarts_text_clipped_count",
            "echarts_text_overlap_pair_count", "echarts_text_measurement_complete",
            "browser_failures", "capture_context",
        },
    )
    expected_root = {
        "design_strategy": request["design_strategy"]["id"],
        "design_version": request["design_strategy"]["version"],
        "manifest_id": manifest["manifest_id"],
        "render_mode": request["render_mode"],
        "author_spec_sha256": manifest["author_spec_sha256"],
    }
    for field, expected in expected_root.items():
        if observed[field] != expected:
            fail(f"runtime attestation observed root {field} does not match contract")
    canvas_pixels = observed["canvas_pixels"]
    if type(canvas_pixels) is not int or canvas_pixels < 0:
        fail("runtime_attestation.observed_root.canvas_pixels must be a nonnegative integer")
    for field in ("echarts_text_count", "echarts_text_clipped_count", "echarts_text_overlap_pair_count"):
        if type(observed[field]) is not int or observed[field] < 0:
            fail(f"runtime_attestation.observed_root.{field} must be a nonnegative integer")
    if observed["echarts_text_measurement_complete"] is not True:
        fail("runtime attestation ECharts text measurement must be complete")
    if observed["echarts_text_clipped_count"] != 0:
        fail("runtime attestation ECharts text clipping must be zero")
    if observed["echarts_text_overlap_pair_count"] != 0:
        fail("runtime attestation ECharts text overlap must be zero")
    validate_successful_browser_failures(observed["browser_failures"])
    if observed["capture_context"] != "adapter_page":
        fail("runtime attestation capture context must be adapter_page")
    if request["render_mode"] == "echarts":
        if observed["adapter_state"] != "trusted-ready":
            fail("observed ECharts adapter state must be trusted-ready")
        if observed["final_action"] != "hold_conclusion":
            fail("observed final ECharts action must be hold_conclusion")
        if canvas_pixels <= 0:
            fail("observed ECharts canvas must contain pixels")
    else:
        if observed["adapter_state"] != "settled":
            fail("observed HTML adapter state must be settled")
        if observed["final_action"] is not None:
            fail("observed HTML final action must be null")
        if canvas_pixels != 0:
            fail("observed HTML canvas pixel count must be zero")
        if observed["echarts_text_count"] != 0:
            fail("observed HTML ECharts text count must be zero")


def validate_artifact_file(
    artifact: dict[str, Any],
    manifest_path: Path,
    cli_path: Path,
    label: str,
) -> None:
    relative = Path(artifact["path"])
    if relative.is_absolute() or len(relative.parts) != 1:
        fail(f"{label} path must be one local filename")
    expected_path = manifest_path.parent / relative
    if cli_path.resolve() != expected_path.resolve():
        fail(f"{label} CLI path does not match manifest artifact path")
    if not expected_path.is_file():
        fail(f"{label} does not exist")
    try:
        raw = expected_path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {label}: {exc}")
    if sha256_bytes(raw) != artifact["sha256"]:
        fail(f"{label} SHA-256 does not match manifest")


def paeth_predictor(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def png_dimensions_and_visibility(raw: bytes) -> tuple[int, int, bool]:
    if len(raw) < 8 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        fail("render screenshot is not a valid PNG")
    offset = 8
    width = height = 0
    bit_depth = color_type = compression = filter_method = interlace = -1
    idat_parts: list[bytes] = []
    saw_ihdr = saw_idat = saw_iend = False
    while offset < len(raw):
        if offset + 12 > len(raw):
            fail("render screenshot is not a complete PNG")
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(raw):
            fail("render screenshot is not a complete PNG")
        chunk_type = raw[offset + 4:offset + 8]
        data = raw[offset + 8:offset + 8 + length]
        supplied_crc = struct.unpack(">I", raw[offset + 8 + length:chunk_end])[0]
        actual_crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
        if supplied_crc != actual_crc:
            fail("render screenshot contains an invalid PNG chunk CRC")
        if chunk_type == b"IHDR":
            if saw_ihdr or offset != 8 or length != 13:
                fail("render screenshot contains an invalid PNG header")
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", data)
            saw_ihdr = True
        elif chunk_type == b"IDAT":
            if not saw_ihdr or saw_iend:
                fail("render screenshot contains an invalid PNG chunk order")
            saw_idat = True
            idat_parts.append(data)
        elif chunk_type == b"IEND":
            if length != 0 or chunk_end != len(raw):
                fail("render screenshot contains an invalid PNG terminator")
            saw_iend = True
        offset = chunk_end
    if not (saw_ihdr and saw_idat and saw_iend):
        fail("render screenshot is not a complete PNG")
    if width <= 0 or height <= 0:
        fail("render screenshot dimensions must be nonzero")
    if width > PNG_MAX_DIMENSION or height > PNG_MAX_DIMENSION:
        fail(f"render screenshot PNG dimensions exceed maximum {PNG_MAX_DIMENSION}")
    if width * height > PNG_MAX_PIXELS:
        fail(f"render screenshot PNG pixel count exceeds maximum {PNG_MAX_PIXELS}")
    if bit_depth != 8 or color_type not in {0, 2, 4, 6} or compression != 0 or filter_method != 0 or interlace != 0:
        fail("render screenshot uses an unsupported PNG pixel format")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    row_bytes = width * channels
    expected_bytes = height * (row_bytes + 1)
    if expected_bytes > PNG_MAX_DECOMPRESSED_BYTES:
        fail(f"render screenshot PNG decompressed byte budget exceeded {PNG_MAX_DECOMPRESSED_BYTES}")
    try:
        decompressor = zlib.decompressobj()
        decompressed = decompressor.decompress(b"".join(idat_parts), expected_bytes + 1)
    except zlib.error as exc:
        fail(f"render screenshot PNG pixel data cannot be decompressed: {exc}")
    if decompressor.unconsumed_tail or len(decompressed) > expected_bytes:
        fail("render screenshot PNG pixel data has an invalid length")
    try:
        decompressed += decompressor.flush()
    except zlib.error as exc:
        fail(f"render screenshot PNG pixel data cannot be decompressed: {exc}")
    if not decompressor.eof or decompressor.unused_data or len(decompressed) != expected_bytes:
        fail("render screenshot PNG pixel data has an invalid length")
    previous = bytearray(row_bytes)
    visible = color_type in {0, 2}
    offset = 0
    for _row_index in range(height):
        filter_type = decompressed[offset]
        offset += 1
        encoded = decompressed[offset:offset + row_bytes]
        offset += row_bytes
        decoded = bytearray(row_bytes)
        for index, byte in enumerate(encoded):
            left = decoded[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = paeth_predictor(left, above, upper_left)
            else:
                fail(f"render screenshot uses unsupported PNG filter {filter_type}")
            decoded[index] = (byte + predictor) & 0xFF
        if color_type in {4, 6}:
            alpha_index = 1 if color_type == 4 else 3
            visible = visible or any(decoded[index] != 0 for index in range(alpha_index, len(decoded), channels))
        previous = decoded
    return width, height, visible


def validate_render_report(
    value: Any,
    report_path: Path,
    request: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    report = strict_object(
        value,
        "render_report",
        {"schema_id", "version", "stage", "manifest_id", "identity", "design_strategy", "render_mode", "renderer", "screenshot", "checks", "runtime_attestation", "final_frame_review_status"},
    )
    reject_public_projection(report, "render_report")
    if report["schema_id"] != "smart-video.render-report.v1" or type(report["version"]) is not int or report["version"] != 1:
        fail("render report schema/version must be smart-video.render-report.v1 version 1")
    if report["stage"] != "trusted_render_validation":
        fail("render_report.stage must be trusted_render_validation")
    if report["manifest_id"] != manifest["manifest_id"]:
        fail("render_report.manifest_id does not match manifest")
    validate_identity(report["identity"], "render_report.identity")
    validate_strategy(report["design_strategy"], "render_report.design_strategy", report)
    for field in ("identity", "design_strategy", "render_mode"):
        if report[field] != request[field]:
            fail(f"render_report.{field} does not match request")
    renderer = strict_object(report["renderer"], "render_report.renderer", {"id", "version", "trust"})
    if renderer["id"] != "smart-video-local-renderer" or renderer["trust"] != "trusted_local":
        fail("render_report.renderer must identify the trusted local renderer")
    require_string(renderer["version"], "render_report.renderer.version")
    screenshot = strict_object(report["screenshot"], "render_report.screenshot", {"path", "sha256", "bytes", "width", "height"})
    relative = Path(require_string(screenshot["path"], "render_report.screenshot.path"))
    if relative.is_absolute() or len(relative.parts) != 1:
        fail("render_report.screenshot.path must be one local filename")
    screenshot_path = report_path.parent / relative
    if not screenshot_path.is_file():
        fail("render screenshot does not exist")
    try:
        file_bytes = screenshot_path.stat().st_size
        if file_bytes > PNG_MAX_FILE_BYTES:
            fail(f"render screenshot PNG compressed file byte budget exceeded {PNG_MAX_FILE_BYTES}")
        raw = screenshot_path.read_bytes()
    except OSError as exc:
        fail(f"cannot read render screenshot: {exc}")
    if not raw:
        fail("render screenshot is empty")
    if require_sha256(screenshot["sha256"], "render_report.screenshot.sha256") != sha256_bytes(raw):
        fail("render screenshot SHA-256 does not match report")
    reported_bytes = require_positive_integer(screenshot["bytes"], "render_report.screenshot.bytes")
    reported_width = require_positive_integer(screenshot["width"], "render_report.screenshot.width")
    reported_height = require_positive_integer(screenshot["height"], "render_report.screenshot.height")
    if reported_bytes != len(raw):
        fail("render screenshot byte count does not match report")
    width, height, visible = png_dimensions_and_visibility(raw)
    if reported_width != width or reported_height != height:
        fail("render screenshot dimensions do not match PNG")
    if not visible:
        fail("render screenshot has no visible nontransparent pixel")
    checks = strict_object(report["checks"], "render_report.checks", RENDER_CHECKS)
    for check in sorted(RENDER_CHECKS):
        if checks[check] != "passed":
            fail(f"render_report.checks.{check} must be passed")
    if report["final_frame_review_status"] != "pending_render":
        fail("render_report.final_frame_review_status must remain pending_render")
    validate_runtime_attestation(report["runtime_attestation"], request, manifest, screenshot["sha256"])
