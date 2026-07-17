"""Local adapter for Podcastor's extracted bespoke HTML contract.

Podcastor's source implementation obtains HTML from its remote generation
step. Smart Slides receives the same HTML from the Codex-authored planning
file, then applies the source sanitizer, geometry guard, and validator before
the renderer sees it.
"""

from __future__ import annotations

import html
import re
from copy import deepcopy
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from backend.services import video_studio_planner as planner
from backend.services import video_studio_visual_styles


class BespokeHtmlContractError(ValueError):
    """A planning file did not provide a renderable director HTML layer."""


_DARK_SVG_BACKDROP = re.compile(r"<rect\b[^>]*>", flags=re.IGNORECASE)
_DARK_SURFACE_COLORS = {"#07111f", "#020617", "#0f172a"}
_EDIT_PROPERTIES = {"text", "x", "y", "width", "height", "fontSize", "scale", "color", "opacity", "motion"}
_EDIT_PROPERTY_ALIASES = {"font_size": "fontSize"}
_EDIT_MARKER_ATTRIBUTE = re.compile(
    r"\s+data-ai-edit-(?:block|kind|name)\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
    flags=re.IGNORECASE,
)
_NON_CONTAINER_TAGS = {
    "area", "base", "br", "circle", "ellipse", "embed", "hr", "img", "input", "line", "link", "meta",
    "path", "polygon", "polyline", "rect", "source", "track", "wbr",
}


@dataclass
class _HtmlElement:
    tag: str
    attrs: dict[str, str]
    start: int
    end: int
    parent: int | None


class _SemanticHtmlCollector(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.elements: list[_HtmlElement] = []
        self.stack: list[int] = []
        self.line_offsets = [0]
        self.line_offsets.extend(match.end() for match in re.finditer(r"\n", source))

    def _source_offset(self) -> int:
        line, column = self.getpos()
        return self.line_offsets[min(max(0, line - 1), len(self.line_offsets) - 1)] + column

    def _record(self, tag: str, attrs: list[tuple[str, str | None]], *, push: bool) -> None:
        start_tag = self.get_starttag_text() or ""
        start = self._source_offset()
        normalized_attrs = {str(key).lower(): str(value or "") for key, value in attrs}
        parent = self.stack[-1] if self.stack else None
        element = _HtmlElement(str(tag).lower(), normalized_attrs, start, start + len(start_tag), parent)
        self.elements.append(element)
        index = len(self.elements) - 1
        if push and element.tag not in _NON_CONTAINER_TAGS and not start_tag.rstrip().endswith("/>"):
            self.stack.append(index)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record(tag, attrs, push=True)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record(tag, attrs, push=False)

    def handle_endtag(self, tag: str) -> None:
        target = str(tag).lower()
        for position in range(len(self.stack) - 1, -1, -1):
            if self.elements[self.stack[position]].tag == target:
                del self.stack[position:]
                return


def _parse_simple_selector(selector: str) -> dict[str, Any]:
    value = str(selector or "").strip()
    if not value:
        raise BespokeHtmlContractError("edit_schema selector 不能为空")
    index = 0
    tag = ""
    element_id = ""
    classes: set[str] = set()
    attrs: dict[str, str | None] = {}
    tag_match = re.match(r"[A-Za-z][\w:-]*", value)
    if tag_match:
        tag = tag_match.group(0).lower()
        index = tag_match.end()
    while index < len(value):
        marker = value[index]
        if marker in {"#", "."}:
            token = re.match(r"[\w-]+", value[index + 1 :])
            if not token:
                raise BespokeHtmlContractError(f"edit_schema 必须使用单元素简单 selector：{value}")
            name = token.group(0)
            if marker == "#":
                if element_id:
                    raise BespokeHtmlContractError(f"edit_schema 必须使用单元素简单 selector：{value}")
                element_id = name
            else:
                classes.add(name)
            index += 1 + len(name)
            continue
        if marker == "[":
            close = value.find("]", index + 1)
            if close < 0:
                raise BespokeHtmlContractError(f"edit_schema 必须使用单元素简单 selector：{value}")
            expression = value[index + 1 : close]
            attr_match = re.fullmatch(r"([A-Za-z_][\w:-]*)(?:=(\"[^\"]*\"|'[^']*'|[^\s\]]+))?", expression)
            if not attr_match:
                raise BespokeHtmlContractError(f"edit_schema 必须使用单元素简单 selector：{value}")
            attr_value = attr_match.group(2)
            if attr_value and attr_value[:1] in {"'", '"'}:
                attr_value = attr_value[1:-1]
            attrs[attr_match.group(1).lower()] = attr_value
            index = close + 1
            continue
        # Whitespace, combinators, comma lists, and pseudo selectors all make
        # ownership ambiguous and are intentionally outside this contract.
        raise BespokeHtmlContractError(f"edit_schema 必须使用单元素简单 selector：{value}")
    if not tag and not element_id and not classes and not attrs:
        raise BespokeHtmlContractError(f"edit_schema 必须使用单元素简单 selector：{value}")
    return {"tag": tag, "id": element_id, "classes": classes, "attrs": attrs}


def _element_matches_selector(element: _HtmlElement, parsed: dict[str, Any]) -> bool:
    if parsed["tag"] and element.tag != parsed["tag"]:
        return False
    if parsed["id"] and element.attrs.get("id") != parsed["id"]:
        return False
    element_classes = set(element.attrs.get("class", "").split())
    if not parsed["classes"].issubset(element_classes):
        return False
    for name, expected in parsed["attrs"].items():
        if name not in element.attrs:
            return False
        if expected is not None and element.attrs[name] != expected:
            return False
    return True


def _normalize_edit_blocks(edit_schema: dict[str, Any]) -> list[dict[str, Any]]:
    if "editable_blocks" not in edit_schema:
        return []
    raw_blocks = edit_schema.get("editable_blocks")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        raise BespokeHtmlContractError("edit_schema editable_blocks 不能为空")
    blocks: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(raw_blocks):
        if not isinstance(raw, dict):
            raise BespokeHtmlContractError(f"edit_schema editable_blocks[{index}] 必须是对象")
        block_id = str(raw.get("id") or "").strip()
        if not block_id or not re.fullmatch(r"[A-Za-z0-9][\w:.-]*", block_id):
            raise BespokeHtmlContractError(f"edit_schema editable_blocks[{index}] 的 id 无效")
        if block_id in ids:
            raise BespokeHtmlContractError(f"edit_schema 存在重复 block id：{block_id}")
        ids.add(block_id)
        name = str(raw.get("name") or "").strip()
        if not name:
            raise BespokeHtmlContractError(f"edit_schema block {block_id} 缺少 name")
        raw_kind = str(raw.get("kind") or raw.get("type") or "").strip()
        if raw_kind == "text":
            kind = "text"
        elif raw_kind in {"group", "visual_group"}:
            kind = "group"
        elif raw_kind == "visual" or raw_kind.startswith("visual_"):
            kind = "visual"
        else:
            raise BespokeHtmlContractError(f"edit_schema block {block_id} 的 kind 无效")
        selector = str(raw.get("selector") or "").strip()
        _parse_simple_selector(selector)
        raw_allowed = raw.get("allowed") if isinstance(raw.get("allowed"), list) else raw.get("controls")
        allowed: list[str] = []
        for item in raw_allowed if isinstance(raw_allowed, list) else []:
            prop = _EDIT_PROPERTY_ALIASES.get(str(item), str(item))
            if prop in _EDIT_PROPERTIES and prop not in allowed:
                allowed.append(prop)
        if not allowed:
            raise BespokeHtmlContractError(f"edit_schema block {block_id} 没有有效的 allowed 属性")
        raw_color_mode = str(raw.get("colorMode") or raw.get("color_mode") or "").strip()
        if raw_color_mode and raw_color_mode not in {"self", "descendants"}:
            raise BespokeHtmlContractError(f"edit_schema block {block_id} 的 colorMode 无效")
        if kind == "group" and "color" in allowed and raw_color_mode != "descendants":
            raise BespokeHtmlContractError(
                f"edit_schema block {block_id} 编辑组颜色时必须声明 colorMode: descendants"
            )
        block = {"id": block_id, "name": name, "kind": kind, "selector": selector, "allowed": allowed}
        if raw_color_mode:
            block["colorMode"] = raw_color_mode
        blocks.append(block)
    return blocks


def normalize_edit_schema(custom_html: str, edit_schema: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """Normalize and mark an authoritative semantic edit schema.

    Legacy selector arrays are returned unchanged for explicit compatibility.
    Once ``editable_blocks`` is present, every selector must identify exactly
    one element and no child block may leak out beneath an editable group.
    """
    source_schema = edit_schema if isinstance(edit_schema, dict) else {}
    blocks = _normalize_edit_blocks(source_schema)
    if not blocks:
        return custom_html, deepcopy(source_schema)

    collector = _SemanticHtmlCollector(custom_html)
    collector.feed(custom_html)
    selected: dict[int, dict[str, Any]] = {}
    selected_elements: dict[str, int] = {}
    for block in blocks:
        parsed = _parse_simple_selector(block["selector"])
        matches = [index for index, element in enumerate(collector.elements) if _element_matches_selector(element, parsed)]
        if len(matches) != 1:
            raise BespokeHtmlContractError(
                f"edit_schema block {block['id']} selector 必须唯一命中 1 个元素，实际 {len(matches)} 个"
            )
        element_index = matches[0]
        if element_index in selected:
            raise BespokeHtmlContractError(
                f"edit_schema block {block['id']} 与 {selected[element_index]['id']} 命中同一元素"
            )
        selected[element_index] = block
        selected_elements[block["id"]] = element_index

    for group in (block for block in blocks if block["kind"] == "group"):
        group_index = selected_elements[group["id"]]
        for block in blocks:
            if block["id"] == group["id"]:
                continue
            parent = collector.elements[selected_elements[block["id"]]].parent
            while parent is not None:
                if parent == group_index:
                    raise BespokeHtmlContractError(
                        f"edit_schema 不允许在可编辑组 {group['id']} 下暴露子块 {block['id']}"
                    )
                parent = collector.elements[parent].parent

    normalized_html = custom_html
    for index in range(len(collector.elements) - 1, -1, -1):
        element = collector.elements[index]
        start_tag = normalized_html[element.start : element.end]
        # Offsets remain valid because replacements run from the end backwards.
        clean_tag = _EDIT_MARKER_ATTRIBUTE.sub("", start_tag)
        block = selected.get(index)
        if block:
            attributes = (
                f' data-ai-edit-block="{html.escape(block["id"], quote=True)}"'
                f' data-ai-edit-kind="{block["kind"]}"'
                f' data-ai-edit-name="{html.escape(block["name"], quote=True)}"'
            )
            if clean_tag.rstrip().endswith("/>"):
                insertion = clean_tag.rfind("/>")
            else:
                insertion = clean_tag.rfind(">")
            clean_tag = clean_tag[:insertion] + attributes + clean_tag[insertion:]
        normalized_html = normalized_html[: element.start] + clean_tag + normalized_html[element.end :]
    return normalized_html, {"version": "edit_schema_v2", "editable_blocks": blocks}


def _edit_override_entries(edit_schema: dict[str, Any], overrides: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    blocks = _normalize_edit_blocks(edit_schema)
    if not blocks:
        if overrides:
            raise BespokeHtmlContractError("语义 edit_schema 缺少 editable_blocks")
        return []
    if not isinstance(overrides, dict):
        raise BespokeHtmlContractError("HTML block overrides 必须是对象")
    by_id = {block["id"]: block for block in blocks}
    entries: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for block_id, raw_properties in overrides.items():
        block = by_id.get(str(block_id))
        if not block:
            raise BespokeHtmlContractError(f"edit_schema 不包含 block {block_id}")
        if not isinstance(raw_properties, dict):
            raise BespokeHtmlContractError(f"block {block_id} override 必须是对象")
        properties: dict[str, Any] = {}
        for raw_property, value in raw_properties.items():
            prop = str(raw_property)
            if prop not in block["allowed"]:
                raise BespokeHtmlContractError(f"block {block_id} 不允许编辑 {prop}")
            if prop == "color" and block["kind"] == "group" and block.get("colorMode") != "descendants":
                raise BespokeHtmlContractError(f"block {block_id} 的组颜色传播需要 colorMode: descendants")
            properties[prop] = value
        entries.append((block, properties))
    return entries


def _finite_number(value: Any, *, block_id: str, prop: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise BespokeHtmlContractError(f"block {block_id} 的 {prop} 必须是数值") from exc
    if not minimum <= number <= maximum:
        raise BespokeHtmlContractError(f"block {block_id} 的 {prop} 超出范围 {minimum:g}..{maximum:g}")
    return number


def _css_number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _safe_css_color(value: Any, *, block_id: str) -> str:
    color = str(value or "").strip()
    semantic_color = re.fullmatch(
        r"var\(\s*--mg-(?:ink|muted|surface|surface-recessed|primary|highlight|danger|outline)\s*\)",
        color,
        flags=re.IGNORECASE,
    )
    hex_color = re.fullmatch(r"#[0-9a-fA-F]{3,8}", color)
    functional_color = re.fullmatch(
        r"(?:rgb|rgba|hsl|hsla)\(\s*[-+0-9.%]+(?:\s*[,/]\s*|\s+[-+0-9.%]+\s*){1,4}\)",
        color,
        flags=re.IGNORECASE,
    )
    named_color = re.fullmatch(r"[A-Za-z]{3,24}", color)
    if not (semantic_color or hex_color or functional_color or named_color):
        raise BespokeHtmlContractError(f"block {block_id} 的 color 无效")
    return color


def build_edit_override_css(edit_schema: dict[str, Any], overrides: dict[str, Any]) -> str:
    """Build scoped CSS containing declarations for supplied properties only."""
    rules: list[str] = []
    motion_keyframes: set[str] = set()
    for block, properties in _edit_override_entries(edit_schema, overrides):
        selector = block["selector"]
        declarations: list[str] = []
        x_or_y = False
        if "x" in properties:
            value = _finite_number(properties["x"], block_id=block["id"], prop="x", minimum=-3840, maximum=3840)
            declarations.append(f"--smart-slides-edit-x:{_css_number(value)}px")
            x_or_y = True
        if "y" in properties:
            value = _finite_number(properties["y"], block_id=block["id"], prop="y", minimum=-2160, maximum=2160)
            declarations.append(f"--smart-slides-edit-y:{_css_number(value)}px")
            x_or_y = True
        if x_or_y:
            declarations.append("translate:var(--smart-slides-edit-x,0px) var(--smart-slides-edit-y,0px)!important")
        numeric_properties = {
            "width": (1, 3840, "width", "px"),
            "height": (1, 2160, "height", "px"),
            "fontSize": (1, 512, "font-size", "px"),
            "scale": (0.05, 10, "scale", ""),
            "opacity": (0, 1, "opacity", ""),
        }
        for prop, (minimum, maximum, css_name, unit) in numeric_properties.items():
            if prop not in properties:
                continue
            value = _finite_number(properties[prop], block_id=block["id"], prop=prop, minimum=minimum, maximum=maximum)
            declarations.append(f"{css_name}:{_css_number(value)}{unit}!important")
        if "motion" in properties:
            motion = str(properties["motion"] or "").strip()
            if motion not in {"none", "fade", "slide", "rise", "wipe", "pop", "scan"}:
                raise BespokeHtmlContractError(f"block {block['id']} 的 motion 无效")
            if motion == "none":
                declarations.append("animation:none!important")
            else:
                animation_name = f"smartSlidesEdit{motion.title()}"
                declarations.append(f"animation-name:{animation_name}!important")
                motion_keyframes.add(motion)
        if declarations:
            rules.append(f"{selector}{{{';'.join(declarations)}}}")
        if "color" in properties:
            color = _safe_css_color(properties["color"], block_id=block["id"])
            color_declarations = f"color:{color}!important"
            if block["kind"] in {"visual", "group"}:
                color_declarations += f";fill:{color}!important;stroke:{color}!important"
            color_selector = f"{selector},{selector} *" if block.get("colorMode") == "descendants" else selector
            rules.append(f"{color_selector}{{{color_declarations}}}")
    keyframes = {
        "fade": "@keyframes smartSlidesEditFade{from{opacity:0}to{opacity:1}}",
        "slide": "@keyframes smartSlidesEditSlide{from{translate:-32px 0;opacity:0}to{translate:0 0;opacity:1}}",
        "rise": "@keyframes smartSlidesEditRise{from{translate:0 24px;opacity:0}to{translate:0 0;opacity:1}}",
        "wipe": "@keyframes smartSlidesEditWipe{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0)}}",
        "pop": "@keyframes smartSlidesEditPop{from{scale:.8;opacity:0}to{scale:1;opacity:1}}",
        "scan": "@keyframes smartSlidesEditScan{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0)}}",
    }
    rules.extend(keyframes[motion] for motion in sorted(motion_keyframes))
    return "\n".join(rules)


def apply_edit_text_overrides(custom_html: str, edit_schema: dict[str, Any], overrides: dict[str, Any]) -> str:
    """Apply only declared text properties while preserving all other markup."""
    result = custom_html
    for block, properties in _edit_override_entries(edit_schema, overrides):
        if "text" not in properties:
            continue
        if block["kind"] != "text":
            raise BespokeHtmlContractError(f"block {block['id']} 不是文字块")
        text_value = str(properties["text"])
        if len(text_value) > 500 or any(ord(character) < 32 and character not in "\n\t" for character in text_value):
            raise BespokeHtmlContractError(f"block {block['id']} 的文字内容无效")
        block_id = re.escape(block["id"])
        matcher = re.compile(
            rf"(<([a-z][\w:-]*)[^>]*data-ai-edit-block=(['\"]){block_id}\3[^>]*>)([\s\S]*?)(</\2>)",
            flags=re.IGNORECASE,
        )
        result, count = matcher.subn(
            lambda match: match.group(1) + html.escape(text_value, quote=False) + match.group(5),
            result,
            count=1,
        )
        if count != 1:
            raise BespokeHtmlContractError(f"block {block['id']} 的文字元素不存在或不唯一")
    return result


def _source_template_surface_css(visual_system: str) -> str:
    """Bring Podcastor's template surface tokens into bespoke overlays.

    This is a small extraction of the original ``.mg-system`` / director
    template styling. It supplies transparent editorial surfaces and a shared
    hierarchy without changing the director-selected SVG composition into a
    template or a card grid.
    """
    return f"""
.ai-mg-layer {{
  --mg-accent: var(--mg-primary);
  --mg-warm: var(--mg-highlight);
  --mg-surface-soft: color-mix(in srgb,var(--mg-surface-recessed) 24%,transparent);
  --mg-surface-local: color-mix(in srgb,var(--mg-surface) 34%,transparent);
  --mg-outline-subtle: color-mix(in srgb,var(--mg-ink) 12%,transparent);
}}
.ai-mg-layer [data-mg-surface="source-translucent"],
.ai-mg-layer .mg-source-surface {{
  fill: color-mix(in srgb,var(--mg-surface) 42%,transparent) !important;
  stroke: var(--mg-outline);
  stroke-width: 1;
}}
.ai-mg-layer .mg-source-panel {{
  background: var(--mg-surface-local);
  border: 1px solid var(--mg-outline);
  backdrop-filter: blur(10px);
}}
.ai-mg-layer .mg-source-label {{
  color: var(--mg-warm);
  font-weight: 950;
  letter-spacing: 0;
}}
.ai-mg-layer .mg-source-enter {{
  opacity: 0;
  transform: translateY(12px);
  animation: smartSlidesSourceEnter .5s ease forwards;
  animation-delay: var(--delay, 0ms);
}}
@keyframes smartSlidesSourceEnter {{ to {{ opacity: 1; transform: translateY(0); }} }}
"""


def _soften_source_dark_backdrops(custom_html: str) -> str:
    """Lower inherited opaque dark SVG backing fields to source-template opacity.

    Existing authored frames used ``#07111f`` at 80% opacity. The original
    Podcastor MG templates use translucent ``rgba(2,6,23,.24/.34)`` surfaces.
    Only explicitly dark, already translucent rects are migrated. An author
    can preserve an intentional opaque field with ``data-mg-opaque="true"``.
    """

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r"\bdata-mg-opaque\s*=\s*(['\"])true\1", tag, flags=re.IGNORECASE):
            return tag
        fill = re.search(r"\bfill\s*=\s*(['\"])(#[0-9a-f]{6})\1", tag, flags=re.IGNORECASE)
        opacity = re.search(r"\bfill-opacity\s*=\s*(['\"])([0-9.]+)\1", tag, flags=re.IGNORECASE)
        if not fill or not opacity:
            return tag
        try:
            if float(opacity.group(2)) < 0.60:
                return tag
        except ValueError:
            return tag
        source_dark = fill.group(2).lower() in _DARK_SURFACE_COLORS
        dimensions = {
            name: float(value)
            for name, _, value in re.findall(r"\b(width|height)\s*=\s*(['\"])([0-9.]+)\2", tag, flags=re.IGNORECASE)
        }
        large_backdrop = dimensions.get("width", 0) >= 800 and dimensions.get("height", 0) >= 540
        if not source_dark and not large_backdrop:
            return tag
        # Preserve a director's colored field, but bring its opacity down to
        # the source template's transparent editorial-surface range.
        target_opacity = ".42" if source_dark else ".38"
        tag = re.sub(r"\bfill-opacity\s*=\s*(['\"])[0-9.]+\1", f'fill-opacity="{target_opacity}"', tag, count=1, flags=re.IGNORECASE)
        if not source_dark:
            return tag
        if tag.endswith("/>"):
            return tag[:-2] + ' data-mg-surface="source-translucent"/>'
        return tag[:-1] + ' data-mg-surface="source-translucent">'

    return _DARK_SVG_BACKDROP.sub(replace, custom_html)


def restore_bespoke_html_from_planning_input(
    source_scene_groups: list[dict[str, Any]], normalized_scene_groups: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Restore authored HTML after Podcastor normalizes storyboard fields.

    The source planner generates bespoke HTML after normalization, so its
    normalizer intentionally does not retain a pre-existing `html_design`.
    Smart Slides receives that HTML in its planning file before normalization.
    When scaling splits an authored shot into multiple source-sized shots, the
    same director HTML is deliberately attached to each segment rather than
    replacing it with a generic template.
    """
    source_shots = [
        shot
        for group in source_scene_groups
        if isinstance(group, dict)
        for shot in group.get("shots") or []
        if isinstance(shot, dict)
    ]
    normalized_shots = [
        shot
        for group in normalized_scene_groups
        if isinstance(group, dict)
        for shot in group.get("shots") or []
        if isinstance(shot, dict)
    ]
    restored = deepcopy(normalized_scene_groups)
    restored_shots = [
        shot
        for group in restored
        for shot in group.get("shots") or []
        if isinstance(shot, dict)
    ]
    if not source_shots:
        return restored

    source_boundaries: list[float] = []
    elapsed = 0.0
    for source in source_shots:
        elapsed += max(0.5, float(source.get("duration_seconds") or 0.5))
        source_boundaries.append(elapsed)

    elapsed = 0.0
    source_index = 0
    for target in restored_shots:
        while source_index < len(source_boundaries) - 1 and elapsed >= source_boundaries[source_index] - 0.001:
            source_index += 1
        source = source_shots[source_index]
        source_design = source.get("html_design") if isinstance(source.get("html_design"), dict) else {}
        authored = {
            key: deepcopy(source_design[key])
            for key in ("custom_html", "custom_css", "layout_summary", "edit_schema")
            if key in source_design
        }
        if authored:
            target["html_design"] = {**(target.get("html_design") or {}), **authored}
        elapsed += max(0.5, float(target.get("duration_seconds") or 0.5))
    return restored


def _mark_style_profile(custom_html: str, profile_id: str) -> str:
    if re.search(r"\bdata-mg-style-profile\s*=", custom_html, flags=re.IGNORECASE):
        return re.sub(
            r"\bdata-mg-style-profile\s*=\s*(['\"])[^'\"]*\1",
            f'data-mg-style-profile="{html.escape(profile_id, quote=True)}"',
            custom_html,
            count=1,
            flags=re.IGNORECASE,
        )
    return re.sub(
        r"(<[a-z][^>]*\bclass\s*=\s*(['\"])[^'\"]*\bai-mg-layer\b[^'\"]*\2)([^>]*>)",
        rf'\1 data-mg-style-profile="{html.escape(profile_id, quote=True)}"\3',
        custom_html,
        count=1,
        flags=re.IGNORECASE,
    )


def prepare_bespoke_html_scene_groups(
    topic: str,
    scene_groups: list[dict[str, Any]],
    visual_style_profile: dict[str, Any] | str | None = None,
) -> list[dict[str, Any]]:
    """Validate and attach Codex-authored HTML using Podcastor source helpers."""
    assets_by_shot: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    for group in scene_groups:
        if not isinstance(group, dict):
            continue
        for shot in group.get("shots") or []:
            if not isinstance(shot, dict) or not planner._shot_uses_html(shot):
                continue
            strategy = str(shot.get("html_render_strategy") or "llm_bespoke_html")
            if strategy == "template":
                continue
            if strategy != "llm_bespoke_html":
                failures.append(f"{shot.get('id') or shot.get('title')}: unsupported HTML render strategy {strategy}")
                continue

            shot_id = str(shot.get("id") or "")
            html_design = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
            custom_html = planner._minify_custom_html_fragment(
                planner._sanitize_custom_html_fragment(str(html_design.get("custom_html") or ""))
            )
            custom_html = _soften_source_dark_backdrops(custom_html)
            authored_custom_css = planner._minify_custom_css(
                planner._sanitize_custom_css(str(html_design.get("custom_css") or ""))
            )
            if not custom_html:
                failures.append(f"{shot_id or shot.get('title')}: llm_bespoke_html requires html_design.custom_html")
                continue

            mg_director = shot.get("mg_director") if isinstance(shot.get("mg_director"), dict) else {}
            resolved_style_profile = video_studio_visual_styles.resolve_visual_style_profile(
                topic=topic,
                requested=mg_director.get("visual_style_profile") or visual_style_profile,
            )
            mg_director = {**mg_director, "visual_style_profile": resolved_style_profile}
            shot["mg_director"] = mg_director
            clip = planner._mg_clip_for_shot(shot)
            overlay_contract = planner._html_overlay_contract_for_clip(topic, clip, [shot])
            visual_system = str(overlay_contract.get("visual_system") or "comparison")
            if "ai-mg-layer" not in custom_html or 'data-ai-generated-html="true"' not in custom_html:
                custom_html = planner._minify_custom_html_fragment(
                    f'<main class="ai-mg-layer ai-mg-layer--{html.escape(visual_system, quote=True)}" '
                    f'data-ai-generated-html="true" data-mg-clip-id="{html.escape(str(clip.get("id") or ""), quote=True)}">'
                    f"{custom_html}</main>"
                )
            custom_html = _mark_style_profile(custom_html, resolved_style_profile["id"])
            visual_recipe = mg_director.get("visual_recipe") if isinstance(mg_director.get("visual_recipe"), dict) else {}
            material_id = str(visual_recipe.get("material_id") or "editorial_color_field")
            style_validation = video_studio_visual_styles.validate_authored_style(
                custom_html,
                authored_custom_css,
                resolved_style_profile,
                material_id=material_id,
            )
            if style_validation.get("errors"):
                failures.append(
                    f"{shot_id or shot.get('title')}: "
                    + "；".join(str(item) for item in style_validation["errors"][:3])
                )
                continue
            custom_css = (
                planner._base_bespoke_html_css(visual_system)
                + "\n"
                + _source_template_surface_css(visual_system)
                + "\n"
                + video_studio_visual_styles.profile_css(resolved_style_profile)
                + "\n"
                + authored_custom_css
                + "\n"
                + planner._bespoke_html_canvas_guard_css()
            )
            custom_html = planner._activate_bespoke_html_layers(custom_html)
            custom_html, custom_css = planner._normalize_bespoke_html_font_sizes(custom_html, custom_css)
            generation = html_design.get("ai_html_generation") if isinstance(html_design.get("ai_html_generation"), dict) else {}
            edit_schema = html_design.get("edit_schema") if isinstance(html_design.get("edit_schema"), dict) else generation.get("edit_schema")
            custom_html, edit_schema = normalize_edit_schema(
                custom_html,
                edit_schema if isinstance(edit_schema, dict) else {},
            )
            validation = planner._validate_bespoke_html_asset(
                custom_html=custom_html,
                custom_css=custom_css,
                edit_schema=edit_schema,
                overlay_contract=overlay_contract,
            )
            validation["style_profile"] = style_validation
            validation["warnings"] = [
                *style_validation.get("warnings", []),
                *validation.get("warnings", []),
            ][:8]
            validation["metrics"] = {
                **(validation.get("metrics") if isinstance(validation.get("metrics"), dict) else {}),
                "style_profile": style_validation.get("metrics") if isinstance(style_validation.get("metrics"), dict) else {},
            }
            if validation.get("errors"):
                failures.append(
                    f"{shot_id or shot.get('title')}: " + "；".join(str(item) for item in validation["errors"][:3])
                )
                continue

            assets_by_shot[shot_id] = {
                "version": "bespoke_html_asset_v1",
                "source": "codex_local_bespoke_html",
                "model": "codex",
                "clip_id": str(clip.get("id") or ""),
                "visual_system": visual_system,
                "style_baseline": "smart_slides_visual_style_profile_v1",
                "visual_style_profile": resolved_style_profile,
                "overlay_contract": overlay_contract,
                "custom_html": custom_html,
                "custom_css": custom_css,
                "layout_summary": str(
                    html_design.get("layout_summary")
                    or mg_director.get("main_visual_metaphor")
                    or ""
                ),
                "edit_schema": edit_schema,
                "validation": validation,
            }

    if failures:
        raise BespokeHtmlContractError("Bespoke HTML contract failed: " + " | ".join(failures))
    return planner._apply_bespoke_html_assets_to_scene_groups(deepcopy(scene_groups), assets_by_shot)
