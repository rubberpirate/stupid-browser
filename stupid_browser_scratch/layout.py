from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter

from .constants import HSTEP, VSTEP
from .dom import Element, Node, Text

_FONT_CACHE: dict[tuple[int, str, bool, bool], QFont] = {}


def _parse_px(value: str, fallback: float) -> float:
    raw = value.strip().lower()
    if raw.endswith("px"):
        raw = raw[:-2]
    try:
        return float(raw)
    except ValueError:
        return fallback


def _font_family(style: dict[str, str]) -> str:
    raw = style.get("font-family", "Georgia")
    first = raw.split(",", 1)[0].strip().strip('"').strip("'")
    lowered = first.lower()

    if lowered in {"serif"}:
        return "Georgia"
    if lowered in {"sans-serif", "sans"}:
        return "Helvetica"
    if lowered in {"monospace", "mono"}:
        return "Courier"

    return first or "Georgia"


def _safe_color(value: str) -> QColor:
    color = QColor(value)
    if color.isValid():
        return color
    return QColor("#1f2937")


def font_for_style(style: dict[str, str]) -> QFont:
    size_px = _parse_px(style.get("font-size", "16px"), 16.0)
    size_px = max(8, int(round(size_px)))

    weight = style.get("font-weight", "normal")
    is_bold = weight == "bold"

    slant = style.get("font-style", "normal")
    is_italic = slant == "italic"

    family = _font_family(style)
    key = (size_px, family, is_bold, is_italic)

    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached

    font = QFont(family)
    font.setPixelSize(size_px)
    font.setBold(is_bold)
    font.setItalic(is_italic)

    _FONT_CACHE[key] = font
    return font


class DrawText:
    def __init__(self, x: float, y: float, text: str, font: QFont, color: str):
        self.left = x
        self.top = y
        self.text = text
        self.font = font
        self.color = color
        metrics = QFontMetricsF(font)
        self.ascent = metrics.ascent()
        self.bottom = y + metrics.height()

    def draw(self, painter: QPainter, scroll: float) -> None:
        painter.setPen(_safe_color(self.color))
        painter.setFont(self.font)
        baseline = self.top - scroll + self.ascent
        painter.drawText(QPointF(self.left, baseline), self.text)


class DrawRect:
    def __init__(self, x1: float, y1: float, x2: float, y2: float, color: str):
        self.left = x1
        self.top = y1
        self.right = x2
        self.bottom = y2
        self.color = color

    def draw(self, painter: QPainter, scroll: float) -> None:
        painter.fillRect(
            QRectF(
                self.left,
                self.top - scroll,
                self.right - self.left,
                self.bottom - self.top,
            ),
            _safe_color(self.color),
        )


class LayoutObject:
    def __init__(
        self,
        node: Node,
        parent: LayoutObject | DocumentLayout,
        previous: LayoutObject | None,
    ):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children: list[LayoutObject] = []
        self.x = 0.0
        self.y = 0.0
        self.width = 0.0
        self.height = 0.0

    def paint(self, display_list: list[DrawText | DrawRect]) -> None:
        for child in self.children:
            child.paint(display_list)


class TextLayout(LayoutObject):
    def __init__(
        self,
        node: Node,
        text: str,
        parent: LineLayout,
        previous: TextLayout | None,
        append_space: bool,
    ):
        super().__init__(node, parent, previous)
        self.text = text
        self.append_space = append_space
        self.trailing_space = 0.0
        self.font: QFont | None = None
        self.metrics: QFontMetricsF | None = None

    def layout(self) -> None:
        self.font = font_for_style(self.node.style)
        self.metrics = QFontMetricsF(self.font)
        self.width = self.metrics.horizontalAdvance(self.text)
        self.height = self.metrics.height()

        if self.previous is None:
            self.x = self.parent.x
        else:
            self.x = self.previous.x + self.previous.width + self.previous.trailing_space

        self.trailing_space = self.metrics.horizontalAdvance(" ") if self.append_space else 0.0

    def paint(self, display_list: list[DrawText | DrawRect]) -> None:
        if not self.text:
            return
        if self.font is None:
            return
        color = self.node.style.get("color", "black")
        display_list.append(DrawText(self.x, self.y, self.text, self.font, color))


class LineLayout(LayoutObject):
    def __init__(
        self,
        node: Node,
        parent: BlockLayout,
        previous: LineLayout | None,
    ):
        super().__init__(node, parent, previous)
        self.children: list[TextLayout] = []

    def layout(self) -> None:
        self.x = self.parent.x
        self.width = self.parent.width

        if self.previous is None:
            self.y = self.parent.y
        else:
            self.y = self.previous.y + self.previous.height

        for child in self.children:
            child.layout()

        if not self.children:
            self.height = 0
            return

        metrics = [child.metrics for child in self.children if child.metrics is not None]
        if not metrics:
            self.height = 0
            return

        max_ascent = max(metric.ascent() for metric in metrics)
        max_descent = max(metric.descent() for metric in metrics)
        baseline = self.y + 1.2 * max_ascent

        for child in self.children:
            if child.metrics is not None:
                child.y = baseline - child.metrics.ascent()

        self.height = max(1.0, 1.25 * (max_ascent + max_descent))

    def paint(self, display_list: list[DrawText | DrawRect]) -> None:
        for child in self.children:
            child.paint(display_list)


class BlockLayout(LayoutObject):
    def __init__(
        self,
        node: Node,
        parent: BlockLayout | DocumentLayout,
        previous: BlockLayout | None,
    ):
        super().__init__(node, parent, previous)
        self.children: list[BlockLayout | LineLayout] = []
        self._cursor_x = 0.0
        self._previous_run: TextLayout | None = None

    def layout(self) -> None:
        self.x = self.parent.x
        self.width = self.parent.width

        if self.previous is None:
            self.y = self.parent.y
        else:
            self.y = self.previous.y + self.previous.height

        if self.node.style.get("display", "inline") == "none":
            self.height = 0
            return

        mode = self._layout_mode()
        if mode == "block":
            previous_child: BlockLayout | None = None
            for child in self.node.children:
                if child.style.get("display", "inline") == "none":
                    continue
                layout_child = BlockLayout(child, self, previous_child)
                self.children.append(layout_child)
                previous_child = layout_child

            for child in self.children:
                child.layout()

            self.height = sum(child.height for child in self.children)
            return

        self._new_line()
        self._recurse_inline(self.node, in_pre=False)

        for line in self.children:
            line.layout()

        self.height = sum(line.height for line in self.children)
        if self.height == 0:
            fallback_font = font_for_style(self.node.style)
            self.height = QFontMetricsF(fallback_font).height()

    def _layout_mode(self) -> str:
        if isinstance(self.node, Text):
            return "inline"

        display = self.node.style.get("display", "inline")
        if display in {"block", "inline", "none"}:
            if display == "inline":
                for child in self.node.children:
                    if isinstance(child, Element) and child.style.get("display") == "block":
                        return "block"
            return display

        return "inline"

    def _new_line(self) -> None:
        previous = self.children[-1] if self.children else None
        self.children.append(LineLayout(self.node, self, previous))
        self._cursor_x = 0.0
        self._previous_run = None

    def _current_line(self) -> LineLayout:
        return self.children[-1]

    def _recurse_inline(self, node: Node, in_pre: bool) -> None:
        if isinstance(node, Text):
            self._add_text_tokens(node, in_pre)
            return

        if isinstance(node, Element):
            if node.style.get("display") == "none":
                return

            if node.tag == "br":
                self._new_line()
                return

            child_in_pre = in_pre or node.tag == "pre"
            for child in node.children:
                self._recurse_inline(child, child_in_pre)

    def _add_text_tokens(self, node: Text, in_pre: bool) -> None:
        if not node.text:
            return

        if in_pre:
            tokens = re.findall(r"\n|[ ]+|[^ \n]+", node.text)
            for token in tokens:
                if token == "\n":
                    self._new_line()
                    continue
                self._add_token(node, token, append_space=False)
            return

        for word in node.text.split():
            self._add_token(node, word, append_space=True)

    def _add_token(self, node: Node, token: str, append_space: bool) -> None:
        if not token:
            return

        probe_font = font_for_style(node.style)
        probe_metrics = QFontMetricsF(probe_font)
        token_width = probe_metrics.horizontalAdvance(token)

        line = self._current_line()
        if line.children and self._cursor_x + token_width > self.width:
            self._new_line()
            line = self._current_line()

        run = TextLayout(node, token, line, self._previous_run, append_space)
        line.children.append(run)
        self._previous_run = run

        self._cursor_x += token_width
        if append_space:
            self._cursor_x += probe_metrics.horizontalAdvance(" ")

    def paint(self, display_list: list[DrawText | DrawRect]) -> None:
        bg = self.node.style.get("background-color", "transparent").strip().lower()
        if bg and bg not in {"transparent", "none"}:
            x2 = self.x + self.width
            y2 = self.y + self.height
            display_list.append(DrawRect(self.x, self.y, x2, y2, bg))

        for child in self.children:
            child.paint(display_list)


class DocumentLayout:
    def __init__(self, node: Node, viewport_width: int):
        self.node = node
        self.viewport_width = viewport_width
        self.x = float(HSTEP)
        self.y = float(VSTEP)
        self.width = max(150.0, float(viewport_width - 2 * HSTEP))
        self.height = 0.0
        self.children: list[BlockLayout] = []

    def layout(self) -> None:
        root_child = BlockLayout(self.node, self, None)
        self.children = [root_child]
        root_child.layout()
        self.height = root_child.height + 2 * VSTEP

    def paint(self, display_list: list[DrawText | DrawRect]) -> None:
        if self.children:
            self.children[0].paint(display_list)


def layout_to_list(layout: DocumentLayout | LayoutObject, out: list[object]) -> list[object]:
    out.append(layout)
    children = getattr(layout, "children", [])
    for child in children:
        layout_to_list(child, out)
    return out
