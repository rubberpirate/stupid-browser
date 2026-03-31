from __future__ import annotations

from .constants import BLOCK_ELEMENTS, HIDDEN_BY_DEFAULT
from .css_parser import CSSRule, parse_declarations
from .dom import Element, Node

INHERITED_DEFAULTS = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "font-family": "Georgia",
    "color": "#1f2937",
}


def apply_styles(root: Node, rules: list[CSSRule]) -> None:
    ordered = sorted(rules, key=lambda rule: (rule.selector.specificity, rule.order))
    _style_node(root, None, ordered)


def _style_node(
    node: Node,
    parent_style: dict[str, str] | None,
    ordered_rules: list[CSSRule],
) -> None:
    style: dict[str, str] = {}

    for prop, default_value in INHERITED_DEFAULTS.items():
        style[prop] = parent_style[prop] if parent_style else default_value

    style["background-color"] = "transparent"
    style["display"] = _default_display(node)
    style["line-height"] = "1.35"

    if isinstance(node, Element):
        for rule in ordered_rules:
            if rule.selector.matches(node):
                style.update(rule.declarations)

        inline_style = node.attributes.get("style")
        if inline_style:
            style.update(parse_declarations(inline_style))

    parent_font_px = 16.0
    if parent_style:
        parent_font_px = _to_px(parent_style.get("font-size", "16px"), 16.0)

    font_px = _to_px(style.get("font-size", "16px"), parent_font_px)
    style["font-size"] = _format_px(font_px)
    style["font-weight"] = _normalize_weight(style.get("font-weight", "normal"))
    style["font-style"] = _normalize_style(style.get("font-style", "normal"))
    style["display"] = _normalize_display(style.get("display", "inline"), _default_display(node))

    line_height_px = _resolve_line_height(style.get("line-height", "1.35"), font_px)
    style["line-height"] = _format_px(line_height_px)

    if not style.get("font-family"):
        style["font-family"] = INHERITED_DEFAULTS["font-family"]

    node.style = style

    for child in node.children:
        _style_node(child, style, ordered_rules)


def _default_display(node: Node) -> str:
    if not isinstance(node, Element):
        return "inline"
    if node.tag in HIDDEN_BY_DEFAULT:
        return "none"
    if node.tag in BLOCK_ELEMENTS:
        return "block"
    return "inline"


def _normalize_display(value: str, fallback: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"inline", "block", "none"}:
        return normalized
    return fallback


def _normalize_style(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"normal", "italic"}:
        return normalized
    return "normal"


def _normalize_weight(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"normal", "bold"}:
        return normalized

    if normalized.isdigit():
        return "bold" if int(normalized) >= 550 else "normal"

    return "normal"


def _resolve_line_height(value: str, font_px: float) -> float:
    raw = value.strip().lower()

    if raw.endswith("px"):
        return max(_float_or_default(raw[:-2], 1.35 * font_px), 8.0)

    if raw.endswith("%"):
        pct = _float_or_default(raw[:-1], 135.0) / 100.0
        return max(font_px * pct, 8.0)

    number = _float_or_default(raw, 1.35)
    if number <= 0:
        number = 1.35
    return max(font_px * number, 8.0)


def _to_px(value: str, parent_px: float) -> float:
    raw = value.strip().lower()

    if raw.endswith("px"):
        return max(_float_or_default(raw[:-2], parent_px), 1.0)
    if raw.endswith("%"):
        pct = _float_or_default(raw[:-1], 100.0) / 100.0
        return max(parent_px * pct, 1.0)
    if raw.endswith("em"):
        scale = _float_or_default(raw[:-2], 1.0)
        return max(parent_px * scale, 1.0)
    if raw.endswith("rem"):
        scale = _float_or_default(raw[:-3], 1.0)
        return max(16.0 * scale, 1.0)

    return max(_float_or_default(raw, parent_px), 1.0)


def _float_or_default(raw: str, default: float) -> float:
    try:
        return float(raw)
    except ValueError:
        return default


def _format_px(value: float) -> str:
    compact = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{compact}px"
