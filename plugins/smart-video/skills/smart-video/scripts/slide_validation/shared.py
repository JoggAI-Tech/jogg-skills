"""Shared errors, bounded traversal, and primitive validation helpers."""

from __future__ import annotations

import json
import math
import re
from typing import Any

JSON_MAX_DEPTH = 128
JSON_MAX_NODES = 100_000
JSON_MAX_STRING_LENGTH = 1_000_000
JSON_MAX_ARRAY_LENGTH = 10_000
JS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
JS_LINE_COMMENT_RE = re.compile(r"//[^\r\n]*")

class ValidationError(Exception):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def scan_json_nesting(raw: str, label: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in raw:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > JSON_MAX_DEPTH:
                fail(f"{label} JSON nesting exceeds maximum depth {JSON_MAX_DEPTH}")
        elif character in "]}":
            depth -= 1


def validate_json_budget(value: Any, label: str) -> None:
    stack: list[tuple[Any, int]] = [(value, 1)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > JSON_MAX_NODES:
            fail(f"{label} JSON node budget exceeded")
        if depth > JSON_MAX_DEPTH:
            fail(f"{label} JSON nesting exceeds maximum depth {JSON_MAX_DEPTH}")
        if isinstance(node, str):
            if len(node) > JSON_MAX_STRING_LENGTH:
                fail(f"{label} JSON string exceeds maximum length {JSON_MAX_STRING_LENGTH}")
        elif isinstance(node, list):
            if len(node) > JSON_MAX_ARRAY_LENGTH:
                fail(f"{label} JSON array exceeds maximum length {JSON_MAX_ARRAY_LENGTH}")
            stack.extend((child, depth + 1) for child in reversed(node))
        elif isinstance(node, dict):
            for key, child in reversed(tuple(node.items())):
                if len(key) > JSON_MAX_STRING_LENGTH:
                    fail(f"{label} JSON object key exceeds maximum length {JSON_MAX_STRING_LENGTH}")
                stack.append((child, depth + 1))


def parse_json_text(text: str, label: str) -> Any:
    scan_json_nesting(text, label)
    try:
        value = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_pairs,
        )
    except ValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"{label} is not valid JSON: {exc}")
    validate_json_budget(value, label)
    return value


def strict_object(value: Any, path: str, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    optional = optional or set()
    missing = sorted(required - set(value))
    if missing:
        fail(f"{path} is missing required field {missing[0]}")
    unknown = sorted(set(value) - required - optional)
    if unknown:
        fail(f"{path} contains unknown field {unknown[0]}")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{path} must be a non-empty string")
    return value


def require_enum_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        fail(f"{path} must be a string")
    if not value:
        fail(f"{path} must be a non-empty string")
    return value


def is_gl_surface_name(value: str) -> bool:
    return value.lower() == "globe" or value.lower().endswith(("3d", "gl"))


def decode_css_escapes(value: str, path: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(value):
        if value[index] != "\\":
            result.append(value[index])
            index += 1
            continue
        index += 1
        if index >= len(value):
            fail(f"{path} contains a trailing CSS escape")
        if value[index] in "\n\f":
            index += 1
            continue
        if value[index] == "\r":
            index += 1
            if index < len(value) and value[index] == "\n":
                index += 1
            continue
        if value[index] in "0123456789abcdefABCDEF":
            start = index
            while index < len(value) and index - start < 6 and value[index] in "0123456789abcdefABCDEF":
                index += 1
            codepoint = int(value[start:index], 16)
            if index < len(value) and value[index] in " \t\r\n\f":
                if value[index] == "\r" and index + 1 < len(value) and value[index + 1] == "\n":
                    index += 2
                else:
                    index += 1
            if codepoint == 0 or 0xD800 <= codepoint <= 0xDFFF or codepoint > 0x10FFFF:
                result.append("\uFFFD")
            else:
                result.append(chr(codepoint))
            continue
        result.append(value[index])
        index += 1
    return "".join(result)


def normalize_executable_string(value: str) -> str:
    without_blocks = JS_BLOCK_COMMENT_RE.sub(" ", value)
    return JS_LINE_COMMENT_RE.sub(" ", without_blocks)


def require_number(value: Any, path: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"{path} must be a finite number")
    number = float(value)
    if positive and number <= 0:
        fail(f"{path} must be positive")
    return number


def require_positive_integer(value: Any, path: str) -> int:
    if type(value) is not int or value <= 0:
        fail(f"{path} must be a positive integer")
    return value


def reject_constant(value: str) -> Any:
    fail(f"JSON contains non-finite number {value}")


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"JSON contains duplicate key {key}")
        result[key] = value
    return result


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def require_json_pointer(value: Any, path: str) -> str:
    if not isinstance(value, str) or (value and not value.startswith("/")):
        fail(f"{path} must be an RFC 6901 JSON pointer")
    return value


def decode_json_pointer_token(value: str) -> str:
    if re.search(r"~(?:[^01]|$)", value):
        fail(f"invalid JSON pointer escape in {value}")
    return value.replace("~1", "/").replace("~0", "~")


def resolve_json_pointer(document: Any, pointer: str, path: str) -> Any:
    require_json_pointer(pointer, path)
    current = document
    if pointer == "":
        return current
    for raw_token in pointer[1:].split("/"):
        token = decode_json_pointer_token(raw_token)
        if isinstance(current, dict):
            if token not in current:
                fail(f"{path} does not resolve: {pointer}")
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")) or int(token) >= len(current):
                fail(f"{path} does not resolve: {pointer}")
            current = current[int(token)]
        else:
            fail(f"{path} does not resolve: {pointer}")
    return current


def json_leaf_pointers(value: Any, pointer: str = "") -> list[str]:
    stack: list[tuple[Any, str]] = [(value, pointer)]
    leaves: list[str] = []
    while stack:
        node, node_pointer = stack.pop()
        if isinstance(node, dict):
            children = []
            for key, child in node.items():
                escaped = key.replace("~", "~0").replace("/", "~1")
                children.append((child, f"{node_pointer}/{escaped}"))
            stack.extend(reversed(children))
        elif isinstance(node, list):
            stack.extend((child, f"{node_pointer}/{index}") for index, child in reversed(tuple(enumerate(node))))
        else:
            leaves.append(node_pointer)
    return leaves
