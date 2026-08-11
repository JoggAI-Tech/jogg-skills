"""Static HTML, CSS, provenance-root, and source-surface validation."""

from __future__ import annotations

from html.parser import HTMLParser
import math
from pathlib import Path
import re
from typing import Any

from .contracts import *

FORBIDDEN_HTML_ELEMENTS = {
    "script", "canvas", "iframe", "frame", "frameset", "object", "embed",
    "img", "image", "picture", "source", "video", "audio", "track", "link", "base",
    "meta", "area", "portal", "param", "applet", "feimage", "mpath",
    "form", "input", "button", "select", "option", "textarea", "fieldset",
    "label", "datalist", "output", "a", "details", "summary", "dialog",
    "animate", "animatetransform", "animatemotion", "set", "foreignobject",
}
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
URL_RE = re.compile(r"(?:https?:|//|data:|blob:|javascript:|file:)", re.IGNORECASE)
ATTRIBUTE_URL_RE = re.compile(r"url\s*\(", re.IGNORECASE)
RESOURCE_ATTRIBUTES = {
    "src", "srcset", "poster", "background", "formaction", "action", "ping",
    "cite", "manifest", "data", "codebase", "archive", "longdesc", "profile",
}
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_SAFE_FUNCTIONS = {
    "attr", "blur", "brightness", "calc", "circle", "clamp", "conic-gradient",
    "contrast", "counter", "counters", "cross", "cubic-bezier", "drop-shadow",
    "ellipse", "env", "grayscale", "hsl", "hsla", "hue-rotate", "inset",
    "invert", "linear-gradient", "matrix", "matrix3d", "max", "min", "minmax",
    "opacity", "perspective", "polygon", "radial-gradient", "repeat",
    "repeating-conic-gradient", "repeating-linear-gradient", "repeating-radial-gradient",
    "rgb", "rgba", "rotate", "rotate3d", "rotatex", "rotatey", "rotatez",
    "saturate", "scale", "scale3d", "scalex", "scaley", "scalez", "sepia",
    "skew", "skewx", "skewy", "steps", "translate", "translate3d", "translatex",
    "translatey", "translatez", "var",
}
CSS_RESOURCE_FUNCTIONS = {
    "-webkit-image-set", "cross-fade", "element", "image", "image-set", "paint", "url",
}
CSS_RESOURCE_FILENAME_RE = re.compile(
    r"(?:^|[\s,('\"])(?:[.]{0,2}/|[A-Za-z0-9_-]+/)?[A-Za-z0-9_.-]+[.]"
    r"(?:apng|avif|bmp|cur|gif|html?|ico|jpe?g|mjs|png|svg|webp|woff2?|ttf|otf)(?:$|[\s,)'\"])",
    re.IGNORECASE,
)
SOURCE_VISIBLE_DISPLAY_VALUES = {
    "block", "flex", "flow-root", "grid", "inline", "inline-block",
    "inline-flex", "inline-grid", "list-item", "table", "table-cell",
    "table-row",
}
SOURCE_FULL_OPACITY_RE = re.compile(r"(?:1(?:[.]0+)?|100%)")
SOURCE_NONE_ONLY_PROPERTIES = {"filter", "clip-path", "mask", "mask-image", "transform"}
BACKDROP_OPACITY_RE = re.compile(r"(?:0(?:[.]\d+)?|1(?:[.]0+)?|[.]\d+|\d+(?:[.]\d+)?%)")
BACKDROP_OPACITY_PROFILES = {
    "html_only": (0.95, 0.99),
    "avatar_html": (0.95, 0.99),
    "broll_html": (0.20, 0.55),
}

class SlideHTMLParser(HTMLParser):
    def __init__(self, *, allow_trusted_scripts: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.allow_trusted_scripts = allow_trusted_scripts
        self.stack: list[dict[str, Any]] = []
        self.root_attrs: dict[str, str | None] | None = None
        self.root_count = 0
        self.root_depth: int | None = None
        self.root_parent_tag: str | None = None
        self.direct_root_children: list[tuple[int, set[str]]] = []
        self.elements: list[dict[str, Any]] = []
        self.elements_by_serial: dict[int, dict[str, Any]] = {}
        self.tag_counts: dict[str, int] = {}
        self.style_elements: list[dict[str, Any]] = []
        self.outside_text: list[str] = []
        self.marked_outside_content: list[str] = []
        self.styles: list[str] = []
        self.unbound_visible_text: list[str] = []
        self.content_elements: dict[str, list[dict[str, Any]]] = {}
        self.content_order: list[str] = []
        self.annotations: dict[str, list[dict[str, str | None]]] = {}
        self.templates: list[dict[str, Any]] = []
        self.elements_by_id: dict[str, list[dict[str, str | None]]] = {}
        self.script_sources: list[str] = []
        self.in_style = False
        self.in_script = False
        self.script_has_data = False
        self.next_serial = 0

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, push=False)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, push=tag.lower() not in VOID_ELEMENTS)

    def _start(self, tag: str, attrs_list: list[tuple[str, str | None]], *, push: bool) -> None:
        tag = tag.lower()
        attrs: dict[str, str | None] = {}
        for name, value in attrs_list:
            lowered = name.lower()
            if lowered in attrs:
                fail(f"HTML element {tag} contains duplicate attribute {lowered}")
            attrs[lowered] = value
        if tag in FORBIDDEN_HTML_ELEMENTS:
            if not (tag == "script" and self.allow_trusted_scripts):
                fail(f"{tag} element is forbidden")
        for name, value in attrs.items():
            decoded_value = (
                CSS_COMMENT_RE.sub("", decode_css_escapes(value, f"HTML attribute {tag}.{name}"))
                if value is not None else None
            )
            if name.startswith("on"):
                fail(f"event handler attribute {name} is forbidden")
            if name == "style":
                fail("style attributes are forbidden")
            if name in {"contenteditable", "draggable", "tabindex", "autofocus", "accesskey"}:
                fail(f"{name} attribute is forbidden")
            if decoded_value and ATTRIBUTE_URL_RE.search(decoded_value):
                fail(f"url() is forbidden in HTML attribute {tag}.{name}")
            if name in RESOURCE_ATTRIBUTES and not (tag == "script" and name == "src" and self.allow_trusted_scripts):
                fail(f"resource-bearing attribute {name} is forbidden on {tag}")
            if decoded_value and URL_RE.search(decoded_value):
                fail(f"remote or executable URL is forbidden in {tag}.{name}")
            if name in {"href", "xlink:href"} and decoded_value and not decoded_value.startswith("#"):
                fail(f"external asset reference is forbidden in {tag}.{name}")
        marker = attrs.get("data-smart-video-slide") == "true"
        serial = self.next_serial
        self.next_serial += 1
        parent = self.stack[-1] if self.stack else None
        parent_tag = parent["tag"] if parent else None
        parent_serial = parent["serial"] if parent else None
        parent_is_root = bool(parent and parent["is_root"])
        inside_parent_root = bool(parent and parent["inside_root"])
        inside_root = marker or inside_parent_root
        classes = set((attrs.get("class") or "").split())
        is_slide_content = parent_is_root and "slide-content" in classes
        inside_content = bool(parent and (parent["inside_content"] or parent["is_slide_content"]))
        element_record = {
            "serial": serial,
            "tag": tag,
            "parent_tag": parent_tag,
            "parent_serial": parent_serial,
            "inside_root": inside_root,
            "is_root": marker,
            "is_slide_content": is_slide_content,
            "attrs": attrs,
            "classes": classes,
        }
        self.elements.append(element_record)
        self.elements_by_serial[serial] = element_record
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        if marker:
            self.root_count += 1
            if self.root_attrs is None:
                self.root_attrs = attrs
                self.root_depth = len(self.stack)
                self.root_parent_tag = parent_tag
        elif parent_is_root:
            self.direct_root_children.append((serial, classes))
        content_id = attrs.get("data-content-id")
        if content_id is not None:
            require_string(content_id, f"HTML {tag}.data-content-id")
            record = {"serial": serial, "attrs": attrs, "text": []}
            self.content_elements.setdefault(content_id, []).append(record)
            self.content_order.append(content_id)
        annotation_id = attrs.get("data-source-annotation-id")
        if annotation_id is not None:
            require_string(annotation_id, f"HTML {tag}.data-source-annotation-id")
            self.annotations.setdefault(annotation_id, []).append(attrs)
        source_marker_attributes = {
            "data-content-id", "data-source-annotation-id", "data-source-pointer",
            "data-source-value-json",
        }
        if source_marker_attributes & set(attrs) and not inside_content:
            marker_identity = content_id or annotation_id or attrs.get("data-source-pointer") or tag
            self.marked_outside_content.append(str(marker_identity))
        element_id = attrs.get("id")
        if element_id is not None:
            self.elements_by_id.setdefault(element_id, []).append(attrs)
        template_record = None
        if tag == "template":
            template_record = {"attrs": attrs, "text": []}
            self.templates.append(template_record)
        if tag == "style":
            self.in_style = True
            self.style_elements.append(element_record)
        if tag == "script":
            self.in_script = True
            if set(attrs) != {"src"} or not attrs.get("src"):
                fail("trusted adapter script must have exactly one src attribute")
            self.script_sources.append(str(attrs["src"]))
        if push:
            self.stack.append({
                "tag": tag,
                "serial": serial,
                "content_id": content_id,
                "template": template_record,
                "inside_root": inside_root,
                "inside_content": inside_content,
                "is_slide_content": is_slide_content,
                "is_root": marker,
            })

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "style":
            self.in_style = False
        if tag == "script":
            self.in_script = False
        if any(frame["tag"] == tag for frame in self.stack):
            while self.stack:
                current = self.stack.pop()
                if current["tag"] == tag:
                    break

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.styles.append(data)
        elif self.in_script:
            if data.strip():
                self.script_has_data = True
        elif data.strip():
            if not any(frame["inside_root"] for frame in self.stack):
                self.outside_text.append(data)
            template = next((frame["template"] for frame in reversed(self.stack) if frame["template"] is not None), None)
            if template is not None:
                template["text"].append(data)
                return
            content_id = next((frame["content_id"] for frame in reversed(self.stack) if frame["content_id"] is not None), None)
            if content_id is None:
                self.unbound_visible_text.append(data)
            else:
                self.content_elements[content_id][-1]["text"].append(data)


def matching_brace(value: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    fail("CSS contains an unmatched block")


def parse_declarations(value: str, path: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for raw in value.split(";"):
        if not raw.strip():
            continue
        if ":" not in raw:
            fail(f"{path} contains a malformed declaration")
        name, declaration_value = raw.split(":", 1)
        name = name.strip().lower()
        if not re.fullmatch(r"--[a-z0-9_-]+|[a-z][a-z0-9-]*", name):
            fail(f"{path} contains unsupported property {name}")
        if name in declarations:
            fail(f"{path} contains duplicate property {name}")
        declarations[name] = declaration_value.strip()
    return declarations


def css_value_functions(value: str, path: str) -> list[str]:
    functions: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(value):
        character = value[index]
        if quote is not None:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {'"', "'"}:
            quote = character
            index += 1
            continue
        if character.isalpha() or character in {"_", "-"}:
            start = index
            index += 1
            while index < len(value) and (value[index].isalnum() or value[index] in {"_", "-"}):
                index += 1
            name = value[start:index].lower()
            lookahead = index
            while lookahead < len(value) and value[lookahead].isspace():
                lookahead += 1
            if lookahead < len(value) and value[lookahead] == "(":
                functions.append(name)
            continue
        index += 1
    if quote is not None:
        fail(f"{path} contains an unterminated string")
    return functions


def validate_css_declaration_value(property_name: str, value: str, path: str) -> None:
    for function in css_value_functions(value, path):
        if function in CSS_RESOURCE_FUNCTIONS or function not in CSS_SAFE_FUNCTIONS:
            fail(f"CSS resource-producing value is forbidden at {path}")
    if CSS_RESOURCE_FILENAME_RE.search(value):
        fail(f"CSS resource-producing value is forbidden at {path}")


def source_surface_visibility_violation(
    declarations: dict[str, str],
    *,
    require_animation_final_proof: bool = False,
) -> str | None:
    normalized = {name: value.strip().lower() for name, value in declarations.items()}
    opacity = normalized.get("opacity")
    if opacity is not None and SOURCE_FULL_OPACITY_RE.fullmatch(opacity) is None:
        return "opacity must be canonical fully opaque"
    display = normalized.get("display")
    if display is not None and display not in SOURCE_VISIBLE_DISPLAY_VALUES:
        return "display must be one explicit visible keyword"
    visibility = normalized.get("visibility")
    if visibility is not None and visibility != "visible":
        return "visibility must be explicitly visible"
    for property_name in sorted(SOURCE_NONE_ONLY_PROPERTIES):
        value = normalized.get(property_name)
        if value is not None and value != "none":
            return f"{property_name} must be none"
    if require_animation_final_proof:
        if opacity is None or normalized.get("transform") != "none":
            return "animation final state must explicitly prove opacity and transform"
    return None


def keyframe_declaration_blocks(body: str, name: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    position = 0
    while position < len(body):
        while position < len(body) and body[position].isspace():
            position += 1
        if position >= len(body):
            break
        opening = body.find("{", position)
        if opening < 0:
            fail(f"CSS keyframes {name} contains malformed content")
        closing = matching_brace(body, opening)
        blocks.append(parse_declarations(
            body[opening + 1:closing],
            f"CSS keyframes {name} step",
        ))
        position = closing + 1
    return blocks


def css_compound_matches(compound: str, element: dict[str, Any]) -> bool:
    position = 0
    tag_match = re.match(r"(?:[A-Za-z][A-Za-z0-9_-]*|[*])", compound)
    if tag_match is not None:
        tag = tag_match.group(0).lower()
        if tag != "*" and element["tag"] != tag:
            return False
        position = tag_match.end()
    while position < len(compound):
        token = re.match(
            r"(?:#(?P<id>[A-Za-z_][\w-]*)|[.](?P<class>[A-Za-z_][\w-]*)|"
            r"\[(?P<attr>[A-Za-z_:][\w:.-]*)(?:=(?P<quote>['\"]?)(?P<value>[^\]'\"]+)(?P=quote))?\])",
            compound[position:],
        )
        if token is None:
            fail(f"CSS selector contains unsupported syntax: {compound}")
        attrs = element["attrs"]
        if token.group("id") is not None and attrs.get("id") != token.group("id"):
            return False
        if token.group("class") is not None and token.group("class") not in element["classes"]:
            return False
        if token.group("attr") is not None:
            attribute = token.group("attr").lower()
            if attribute not in attrs:
                return False
            if token.group("value") is not None and attrs.get(attribute) != token.group("value"):
                return False
        position += token.end()
    return True


def parse_css_selector(selector: str) -> tuple[list[str], list[str]]:
    compounds: list[str] = []
    combinators: list[str] = []
    position = 0
    for match in re.finditer(r"[^\s>]+", selector):
        if compounds:
            separator = selector[position:match.start()]
            combinators.append("child" if ">" in separator else "descendant")
        compounds.append(match.group(0))
        position = match.end()
    if not compounds or selector[:selector.find(compounds[0])].strip() or selector[position:].strip():
        fail(f"CSS selector contains unsupported syntax: {selector}")
    return compounds, combinators


def css_selector_matches(selector: str, serial: int, parser: SlideHTMLParser) -> bool:
    compounds, combinators = parse_css_selector(selector)

    def match_at(compound_index: int, candidate_serial: int | None) -> bool:
        if candidate_serial is None:
            return False
        candidate = parser.elements_by_serial[candidate_serial]
        if not css_compound_matches(compounds[compound_index], candidate):
            return False
        if compound_index == 0:
            return True
        parent_serial = candidate["parent_serial"]
        if combinators[compound_index - 1] == "child":
            return match_at(compound_index - 1, parent_serial)
        while parent_serial is not None:
            if match_at(compound_index - 1, parent_serial):
                return True
            parent_serial = parser.elements_by_serial[parent_serial]["parent_serial"]
        return False

    return match_at(len(compounds) - 1, serial)


def parse_css(css: str) -> tuple[list[tuple[str, dict[str, str]]], dict[str, str]]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    if re.search(r"url\s*\(", css, re.IGNORECASE):
        fail("CSS URL resources are forbidden")
    rules: list[tuple[str, dict[str, str]]] = []
    keyframes: dict[str, str] = {}
    position = 0
    while position < len(css):
        while position < len(css) and css[position].isspace():
            position += 1
        if position >= len(css):
            break
        opening = css.find("{", position)
        if opening < 0:
            fail("CSS contains content outside a rule")
        header = css[position:opening].strip()
        closing = matching_brace(css, opening)
        body = css[opening + 1:closing]
        if header.startswith("@"):
            match = re.fullmatch(r"@keyframes\s+([A-Za-z_][\w-]*)", header, re.IGNORECASE)
            if match is None:
                at_name = re.match(r"@([\w-]+)", header)
                fail(f"CSS at-rule @{at_name.group(1) if at_name else header[1:]} is forbidden")
            name = match.group(1)
            if name in keyframes:
                fail(f"duplicate CSS keyframes {name}")
            keyframes[name] = body
        else:
            if "{" in body or "}" in body:
                fail("nested CSS rules are forbidden")
            for selector in header.split(","):
                selector = selector.strip()
                if not (selector == "#slide-root" or re.match(r"^#slide-root(?:\s+|\s*>\s*)\S", selector)):
                    fail(f"CSS selector is outside #slide-root: {selector}")
                if ":" in selector:
                    fail("CSS pseudo-selectors are forbidden")
                if re.search(r"[^A-Za-z0-9_#\.\-\[\]=\"'():*+~>\s]", selector):
                    fail(f"CSS selector contains unsupported syntax: {selector}")
                rules.append((selector, parse_declarations(body, f"CSS selector {selector}")))
        position = closing + 1
    return rules, keyframes


def parse_time(value: str, path: str) -> float:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s)", value.strip(), re.IGNORECASE)
    if match is None:
        fail(f"{path} must be one nonnegative CSS time")
    return float(match.group(1)) * (0.001 if match.group(2).lower() == "ms" else 1.0)


def parse_animation(declarations: dict[str, str], selector: str) -> tuple[str, float, float] | None:
    longhands = {key: value for key, value in declarations.items() if key.startswith("animation-")}
    shorthand = declarations.get("animation")
    if shorthand is None and not longhands:
        return None
    if shorthand is not None and longhands:
        fail(f"CSS selector {selector} must not mix animation shorthand and longhands")
    if shorthand is not None:
        if "," in shorthand:
            fail(f"CSS selector {selector} must define exactly one animation")
        tokens = shorthand.split()
        if len(tokens) != 6:
            fail(f"CSS selector {selector} animation shorthand must be name duration easing delay count fill-mode")
        name, duration_value, _easing, delay_value, count, fill_mode = tokens
    else:
        required = {"animation-name", "animation-duration", "animation-delay", "animation-iteration-count", "animation-fill-mode"}
        missing = sorted(required - set(longhands))
        unknown = sorted(set(longhands) - required)
        if missing:
            fail(f"CSS selector {selector} is missing {missing[0]}")
        if unknown:
            fail(f"CSS selector {selector} contains unsupported {unknown[0]}")
        name = longhands["animation-name"]
        duration_value = longhands["animation-duration"]
        delay_value = longhands["animation-delay"]
        count = longhands["animation-iteration-count"]
        fill_mode = longhands["animation-fill-mode"]
    if not re.fullmatch(r"[A-Za-z_][\w-]*", name):
        fail(f"CSS selector {selector} animation name is invalid")
    if count != "1":
        fail(f"CSS animation {name} iteration-count must be exactly 1")
    if fill_mode not in {"both", "forwards"}:
        fail(f"CSS animation {name} must retain its final state")
    duration = parse_time(duration_value, f"CSS animation {name} duration")
    delay = parse_time(delay_value, f"CSS animation {name} delay")
    if duration <= 0:
        fail(f"CSS animation {name} duration must be positive")
    return name, delay, duration


def parse_backdrop_opacity(value: str) -> float:
    normalized = value.strip().lower()
    if BACKDROP_OPACITY_RE.fullmatch(normalized) is None:
        fail("slide-backdrop opacity must be one canonical number or percentage")
    parsed = float(normalized[:-1]) / 100 if normalized.endswith("%") else float(normalized)
    if parsed >= 1.0:
        fail("slide-backdrop opacity must remain below 1.00")
    return parsed


def validate_css(
    css: str,
    manifest: dict[str, Any],
    parser: SlideHTMLParser,
) -> dict[str, tuple[float, float]]:
    css = decode_css_escapes(css, "CSS")
    lowered = css.lower()
    checks = {
        "expression(": "executable CSS expressions are forbidden",
        ":hover": "interactive CSS selectors are forbidden",
        ":focus": "interactive CSS selectors are forbidden",
        ":active": "interactive CSS selectors are forbidden",
        "random(": "random CSS values are forbidden",
    }
    for token, message in checks.items():
        if token in lowered:
            fail(message)
    if URL_RE.search(css):
        fail("remote or executable URL is forbidden in CSS")
    rules, keyframes = parse_css(css)
    if re.search(r"(?:^|[;{])\s*content\s*:", css, re.IGNORECASE):
        fail("CSS generated content is forbidden")
    hold_start = float(manifest["motion_phases"][-1]["start_seconds"])
    animations: dict[str, tuple[float, float]] = {}
    backdrop_serial = next(
        serial
        for serial, classes in parser.direct_root_children
        if "slide-backdrop" in classes
    )
    backdrop_opacities: list[float] = []
    for selector, declarations in rules:
        for property_name, value in declarations.items():
            validate_css_declaration_value(property_name, value, f"CSS selector {selector}.{property_name}")
        root_selector = selector == "#slide-root" or re.fullmatch(r"#slide-root(?:[.#\[].*)", selector) is not None
        if root_selector and "opacity" in declarations:
            fail("opacity on the generated root is forbidden")
        if "content" in declarations:
            fail("CSS generated content is forbidden")
        hides_surface = (
            declarations.get("display", "").lower() == "none"
            or declarations.get("visibility", "").lower() in {"hidden", "collapse"}
            or re.fullmatch(r"(?:0+(?:\.0*)?|\.0+)", declarations.get("opacity", "")) is not None
        )
        affects_source_surface = any(
            css_selector_matches(selector, serial, parser)
            for serial in source_surface_serials(parser)
        )
        if hides_surface and affects_source_surface:
            fail(f"CSS selector {selector} must not hide a source-bearing surface")
        if affects_source_surface:
            violation = source_surface_visibility_violation(declarations)
            if violation is not None:
                fail(f"source-bearing CSS surface {selector} {violation}")
        affects_backdrop = css_selector_matches(selector, backdrop_serial, parser)
        if affects_backdrop and "opacity" in declarations:
            backdrop_opacities.append(parse_backdrop_opacity(declarations["opacity"]))
        animation = parse_animation(declarations, selector)
        if animation is None:
            continue
        name, delay, duration = animation
        end_time = delay + duration
        if root_selector:
            fail("animations on the generated root are forbidden")
        if end_time > hold_start + 1e-9:
            fail(f"CSS animation {name} must finish before stable_hold")
        if name not in keyframes:
            fail(f"CSS animation {name} has no matching @keyframes")
        final_match = re.search(r"(?:^|})\s*(?:to|100%)\s*\{", keyframes[name], re.IGNORECASE)
        if final_match is None:
            fail(f"CSS keyframes {name} must define a final state")
        final_opening = keyframes[name].find("{", final_match.start())
        final_closing = matching_brace(keyframes[name], final_opening)
        final_declarations = parse_declarations(
            keyframes[name][final_opening + 1:final_closing],
            f"CSS keyframes {name} final state",
        )
        if affects_backdrop:
            for step_declarations in keyframe_declaration_blocks(keyframes[name], name):
                if "opacity" in step_declarations:
                    parse_backdrop_opacity(step_declarations["opacity"])
            if "opacity" in final_declarations:
                backdrop_opacities.append(
                    parse_backdrop_opacity(final_declarations["opacity"])
                )
        legacy_zero_opacity = re.fullmatch(
            r"(?:0+(?:\.0*)?|\.0+)",
            final_declarations.get("opacity", ""),
        )
        if legacy_zero_opacity is not None:
            fail(f"CSS keyframes {name} final state must remain visible")
        if affects_source_surface:
            violation = source_surface_visibility_violation(
                final_declarations,
                require_animation_final_proof=True,
            )
            if violation is not None:
                fail(f"CSS keyframes {name} final state must prove source-surface visibility")
            for step_declarations in keyframe_declaration_blocks(keyframes[name], name):
                forbidden_step_properties = (
                    set(step_declarations)
                    & ({"display", "visibility"} | SOURCE_NONE_ONLY_PROPERTIES - {"transform"})
                )
                if forbidden_step_properties:
                    fail(f"CSS keyframes {name} source-surface steps contain unsupported visibility property")
        if (
            final_declarations.get("display", "").lower() == "none"
            or final_declarations.get("visibility", "").lower() == "hidden"
        ):
            fail(f"CSS keyframes {name} final state must remain visible")
        timing = (delay, end_time)
        if name in animations and animations[name] != timing:
            fail(f"CSS animation {name} has inconsistent timing")
        animations[name] = timing
    if not backdrop_opacities:
        fail("slide-backdrop must declare a canonical composition opacity")
    minimum, maximum = BACKDROP_OPACITY_PROFILES[manifest["shot_type"]]
    if any(value < minimum - 1e-9 or value > maximum + 1e-9 for value in backdrop_opacities):
        fail(
            f"slide-backdrop opacity is outside the {manifest['shot_type']} composition profile"
        )
    return animations


def element_is_hidden(element: dict[str, Any]) -> bool:
    attrs = element["attrs"]
    if "hidden" in attrs:
        return True
    aria_hidden = attrs.get("aria-hidden")
    if isinstance(aria_hidden, str) and aria_hidden.strip().lower() == "true":
        return True
    for name, hidden_values in (("display", {"none"}), ("visibility", {"hidden", "collapse"})):
        value = attrs.get(name)
        if isinstance(value, str):
            decoded = CSS_COMMENT_RE.sub("", decode_css_escapes(value, f"HTML attribute {element['tag']}.{name}"))
            if decoded.strip().lower() in hidden_values:
                return True
    opacity = attrs.get("opacity")
    if isinstance(opacity, str):
        decoded = CSS_COMMENT_RE.sub("", decode_css_escapes(opacity, f"HTML attribute {element['tag']}.opacity"))
        if re.fullmatch(r"(?:0+(?:[.]0*)?|[.]0+)", decoded.strip()):
            return True
    return False


def validate_source_element_properties(element: dict[str, Any], label: str) -> None:
    declarations: dict[str, str] = {}
    for property_name in (
        "opacity", "display", "visibility", "filter", "clip-path", "mask",
        "mask-image", "transform",
    ):
        value = element["attrs"].get(property_name)
        if isinstance(value, str):
            declarations[property_name] = CSS_COMMENT_RE.sub(
                "",
                decode_css_escapes(value, f"HTML attribute {element['tag']}.{property_name}"),
            )
    violation = source_surface_visibility_violation(declarations)
    if violation is not None:
        fail(f"source-bearing HTML surface {violation} on {label}")


def source_surface_serials(parser: SlideHTMLParser) -> set[int]:
    serials: set[int] = set()
    for records in parser.content_elements.values():
        for record in records:
            serial: int | None = record["serial"]
            while serial is not None:
                if serial in serials:
                    break
                serials.add(serial)
                serial = parser.elements_by_serial[serial]["parent_serial"]
    return serials


def validate_html_source_visibility(parser: SlideHTMLParser) -> None:
    root = next(element for element in parser.elements if element["is_root"])
    if element_is_hidden(root):
        fail("#slide-root must remain visible")
    validate_source_element_properties(root, "#slide-root")
    content = next(element for element in parser.elements if element["is_slide_content"])
    if element_is_hidden(content):
        fail(".slide-content must remain visible")
    validate_source_element_properties(content, ".slide-content")
    for content_id, records in parser.content_elements.items():
        for record in records:
            serial = record["serial"]
            element = parser.elements_by_serial[serial]
            if element_is_hidden(element):
                fail(f"source-bearing HTML element {content_id} must remain visible")
            validate_source_element_properties(element, content_id)
            ancestor_serial = element["parent_serial"]
            while ancestor_serial is not None:
                ancestor = parser.elements_by_serial[ancestor_serial]
                if ancestor["is_root"] or ancestor["is_slide_content"]:
                    ancestor_serial = ancestor["parent_serial"]
                    continue
                if element_is_hidden(ancestor):
                    fail(f"ancestor of source-bearing HTML element {content_id} must remain visible")
                validate_source_element_properties(ancestor, f"ancestor of {content_id}")
                ancestor_serial = ancestor["parent_serial"]


def source_leaf_text(value: Any) -> str:
    if isinstance(value, str):
        return normalize_text(value)
    return canonical_json_bytes(value).decode("utf-8")


def validate_html_data_binding_targets(parser: SlideHTMLParser, request: dict[str, Any]) -> None:
    bindings = request["html_data_bindings"]
    expected_leaves = json_leaf_pointers(request["source_data"])
    bound_pointers = [binding["source_pointer"] for binding in bindings]
    for pointer in expected_leaves:
        if pointer not in bound_pointers:
            fail(f"source_data leaf {pointer} is unbound")
    for pointer in bound_pointers:
        if pointer not in expected_leaves:
            fail(f"HTML data binding references non-leaf source pointer {pointer}")
    used_content: set[str] = set()
    used_annotations: set[str] = set()
    for binding in bindings:
        pointer = binding["source_pointer"]
        source_value = resolve_json_pointer(request["source_data"], pointer, "HTML source pointer")
        target_id = binding["target_id"]
        if binding["target_type"] == "content":
            records = parser.content_elements.get(target_id, [])
            if len(records) != 1:
                fail(f"content target {target_id} must appear exactly once")
            record = records[0]
            if record["attrs"].get("data-source-pointer") != pointer:
                fail(f"content target {target_id} source pointer does not match binding")
            if normalize_text("".join(record["text"])) != source_leaf_text(source_value):
                fail(f"content target {target_id} does not preserve source value")
            used_content.add(target_id)
        else:
            records = parser.annotations.get(target_id, [])
            if len(records) != 1:
                fail(f"annotation {target_id} must appear exactly once")
            record = records[0]
            if record.get("data-source-pointer") != pointer:
                fail(f"annotation {target_id} source pointer does not match binding")
            raw_value = record.get("data-source-value-json")
            if raw_value is None:
                fail(f"annotation {target_id} is missing data-source-value-json")
            annotation_value = parse_json_text(raw_value, f"annotation {target_id}")
            if canonical_json_bytes(annotation_value) != canonical_json_bytes(source_value):
                fail(f"annotation {target_id} does not preserve source value")
            used_annotations.add(target_id)
    for content_id, records in parser.content_elements.items():
        for record in records:
            if record["attrs"].get("data-source-pointer") is not None and content_id not in used_content:
                fail(f"content target {content_id} has an undeclared source pointer")
    for annotation_id in parser.annotations:
        if annotation_id not in used_annotations:
            fail(f"annotation {annotation_id} has no source binding")


def validate_html(
    path: Path,
    request: dict[str, Any],
    manifest: dict[str, Any],
    *,
    adapter: bool,
    author_spec: dict[str, Any] | None = None,
) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"cannot read HTML artifact: {exc}")
    if "public_projection" in raw:
        fail("public_projection is forbidden in HTML artifact")
    parser = SlideHTMLParser(allow_trusted_scripts=adapter and request["render_mode"] == "echarts")
    try:
        parser.feed(raw)
        parser.close()
    except ValidationError:
        raise
    except (TypeError, ValueError, UnicodeError) as exc:
        fail(f"HTML artifact is malformed: {exc}")
    if parser.root_count != 1 or parser.root_attrs is None:
        fail("HTML must contain exactly one generated root")
    if parser.root_attrs.get("id") != "slide-root":
        fail("generated HTML root id must be slide-root")
    if parser.root_parent_tag != "body":
        fail("generated HTML root must be a direct child of body")
    backdrop_ids = [serial for serial, classes in parser.direct_root_children if "slide-backdrop" in classes]
    content_ids = [serial for serial, classes in parser.direct_root_children if "slide-content" in classes]
    if len(backdrop_ids) == 1 and len(content_ids) == 1 and backdrop_ids[0] == content_ids[0]:
        fail("backdrop and content must be distinct direct children")
    if len(parser.direct_root_children) != 2 or len(backdrop_ids) != 1 or len(content_ids) != 1:
        fail("generated root direct element children must be exactly slide-backdrop and slide-content")
    if backdrop_ids[0] > content_ids[0]:
        fail("slide-backdrop must precede slide-content")
    validate_html_source_visibility(parser)
    if parser.marked_outside_content:
        fail(f"source-marked element {parser.marked_outside_content[0]} must be a descendant of .slide-content")
    if any(normalize_text(value) for value in parser.outside_text):
        fail("non-whitespace text is forbidden outside #slide-root")
    for tag in ("html", "head", "body"):
        if parser.tag_counts.get(tag) != 1:
            fail("HTML artifact must contain exactly one html, head, and body element")
    for element in parser.elements:
        tag = element["tag"]
        if element["is_root"]:
            continue
        if tag == "html":
            if element["parent_tag"] is not None or element["inside_root"]:
                fail("html element has invalid placement")
            continue
        if tag in {"head", "body"}:
            if element["parent_tag"] != "html" or element["inside_root"]:
                fail(f"{tag} element has invalid placement")
            continue
        if tag == "style":
            if element["parent_tag"] != "head" or element["inside_root"]:
                fail("style element must be the direct nonvisual child of head")
            continue
        if tag == "script" and parser.allow_trusted_scripts:
            if element["parent_tag"] != "body" or element["inside_root"]:
                fail("trusted adapter scripts must be direct children of body outside #slide-root")
            continue
        if not element["inside_root"]:
            fail(f"element {tag} is forbidden outside #slide-root")
    if len(parser.style_elements) > 1:
        fail("HTML artifact may contain at most one style element")
    if request["render_mode"] == "html_svg" and len(parser.style_elements) != 1:
        fail("html_svg requires one style element as the direct nonvisual child of head")
    root_strategy = {
        "id": parser.root_attrs.get("data-design-strategy"),
        "version": parser.root_attrs.get("data-design-version"),
        "selection_source": request["design_strategy"]["selection_source"],
    }
    if root_strategy != request["design_strategy"]:
        fail("HTML root design strategy does not match request")
    root_fields = {
        "data-video-id": "video_id",
        "data-shot-id": "shot_id",
        "data-segment-id": "segment_id",
        "data-slide-id": "slide_id",
        "data-clip-id": "clip_id",
    }
    for attribute, field in root_fields.items():
        if parser.root_attrs.get(attribute) != request["identity"][field]:
            fail(f"HTML root {attribute} does not match request identity")
    if parser.root_attrs.get("data-render-mode") != request["render_mode"]:
        fail("HTML root render mode does not match request")
    if parser.root_attrs.get("data-manifest-id") != manifest["manifest_id"]:
        fail("HTML root manifest identity does not match manifest")
    animations = validate_css("\n".join(parser.styles), manifest, parser)
    if request["render_mode"] == "html_svg":
        for phase in manifest["motion_phases"]:
            if phase["state"] == "active" and phase["animation_name"] not in animations:
                if not animations:
                    fail("active HTML motion phases require a finite CSS animation")
                fail(f"active motion phase {phase['id']} requires CSS animation {phase['animation_name']}")
            if phase["state"] == "active":
                start, end = animations[phase["animation_name"]]
                if not math.isclose(start, float(phase["start_seconds"]), abs_tol=1e-9) or not math.isclose(end, float(phase["end_seconds"]), abs_tol=1e-9):
                    fail(f"active motion phase {phase['id']} timing does not match CSS animation {phase['animation_name']}")
    if adapter and request["render_mode"] == "echarts":
        if parser.script_sources != TRUSTED_SCRIPTS or parser.script_has_data:
            fail("ECharts adapter HTML must inject only the exact bundled local scripts")
        expected_hash = manifest["author_spec_sha256"]
        if parser.root_attrs.get("data-author-spec-sha256") != expected_hash:
            fail("ECharts adapter root author-spec SHA-256 is missing or mismatched")
        chart_roots = parser.elements_by_id.get("echarts-root", [])
        if len(chart_roots) != 1 or chart_roots[0].get("data-author-spec-sha256") != expected_hash:
            fail("ECharts adapter chart root author-spec SHA-256 is missing or mismatched")
        templates = [record for record in parser.templates if record["attrs"].get("id") == "echarts-author-spec"]
        if len(templates) != 1 or templates[0]["attrs"].get("data-author-spec-sha256") != expected_hash:
            fail("ECharts adapter embedded author spec linkage is missing or mismatched")
        embedded_spec = parse_json_text(
            "".join(templates[0]["text"]),
            "embedded ECharts author spec",
        )
        if author_spec is None or canonical_json_bytes(embedded_spec) != canonical_json_bytes(author_spec):
            fail("embedded ECharts author spec does not match author artifact")
    elif parser.script_sources:
        fail("script element is forbidden")
    if request["render_mode"] == "html_svg":
        expected_items = request["source_content"]["screen_content"]
        expected_ids = [item["content_id"] for item in expected_items]
        for item in expected_items:
            content_id = item["content_id"]
            records = parser.content_elements.get(content_id, [])
            if len(records) != 1:
                fail(f"rendered content_id {content_id} must appear exactly once")
            if normalize_text("".join(records[0]["text"])) != normalize_text(item["text"]):
                if adapter:
                    fail("HTML omits exact screen_content item value")
                fail(f"rendered content_id {content_id} text does not match request")
        unknown_ids = sorted(set(parser.content_elements) - set(expected_ids))
        if unknown_ids:
            fail(f"rendered content_id {unknown_ids[0]} is not authorized")
        if parser.content_order != expected_ids:
            fail("rendered content_id order does not match request.source_content.screen_content")
        validate_html_data_binding_targets(parser, request)
    if any(normalize_text(value) for value in parser.unbound_visible_text):
        fail("unbound visible text is forbidden")
