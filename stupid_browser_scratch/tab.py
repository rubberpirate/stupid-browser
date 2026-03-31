from __future__ import annotations

import html
from importlib import resources

from PySide6.QtGui import QPainter

from .css_parser import CSSRule, parse_stylesheet
from .dom import Element, Node, Text, walk
from .html_parser import HTMLParser
from .layout import DocumentLayout, DrawRect, DrawText, layout_to_list
from .network import URL
from .style import apply_styles


class Tab:
    def __init__(self, viewport_width: int, viewport_height: int, home_url: str):
        self.viewport_width = max(200, viewport_width)
        self.viewport_height = max(120, viewport_height)
        self.scroll = 0

        self.home_url = URL(home_url)
        self.current_url = self.home_url

        self.history: list[URL] = []
        self.history_index = -1

        self.dom: Node | None = None
        self.document: DocumentLayout | None = None
        self.display_list: list[DrawText | DrawRect] = []

        self.default_rules = self._load_default_stylesheet()

    def _load_default_stylesheet(self) -> list[CSSRule]:
        css_text = resources.files("stupid_browser_scratch").joinpath("default.css").read_text(
            encoding="utf-8"
        )
        return parse_stylesheet(css_text)

    def set_viewport(self, width: int, height: int) -> None:
        self.viewport_width = max(200, width)
        self.viewport_height = max(120, height)
        self._relayout()

    def open(self, value: str | URL, add_history: bool = True) -> None:
        url = value if isinstance(value, URL) else URL(value)
        self._load(url, add_history=add_history)

    def _load(self, url: URL, add_history: bool) -> None:
        try:
            _, body, final_url = url.request()
        except Exception as exc:
            body = self._error_document(url, exc)
            final_url = url

        self.dom = HTMLParser(body).parse()

        rules = list(self.default_rules)
        rules.extend(self._collect_css_rules(self.dom, final_url))
        apply_styles(self.dom, rules)

        self.current_url = final_url
        self.scroll = 0
        self._relayout()

        if add_history:
            if self.history_index < len(self.history) - 1:
                self.history = self.history[: self.history_index + 1]
            self.history.append(final_url)
            self.history_index = len(self.history) - 1

    def _collect_css_rules(self, root: Node, base_url: URL) -> list[CSSRule]:
        rules: list[CSSRule] = []

        for node in walk(root):
            if not isinstance(node, Element):
                continue

            if node.tag == "style":
                css_text = "".join(
                    child.text for child in node.children if isinstance(child, Text)
                )
                rules.extend(parse_stylesheet(css_text))
                continue

            if node.tag != "link":
                continue

            rel = node.attributes.get("rel", "")
            if "stylesheet" not in rel.lower().split():
                continue

            href = node.attributes.get("href")
            if not href:
                continue

            try:
                _, css_text, _ = base_url.resolve(href).request()
            except Exception:
                continue

            rules.extend(parse_stylesheet(css_text))

        return rules

    def _error_document(self, url: URL, exc: Exception) -> str:
        message = html.escape(str(exc))
        return (
            "<html><body>"
            "<h1>Load error</h1>"
            f"<p>Could not open <b>{html.escape(str(url))}</b></p>"
            f"<pre>{message}</pre>"
            "</body></html>"
        )

    def _relayout(self) -> None:
        if self.dom is None:
            return

        self.document = DocumentLayout(self.dom, self.viewport_width)
        self.document.layout()

        self.display_list = []
        self.document.paint(self.display_list)
        self.scroll = min(self.scroll, self.max_scroll)

    @property
    def max_scroll(self) -> int:
        if self.document is None:
            return 0
        return max(0, int(self.document.height - self.viewport_height))

    def scroll_by(self, delta: int) -> None:
        self.scroll = max(0, min(self.scroll + delta, self.max_scroll))

    def draw(self, painter: QPainter) -> None:
        if self.document is None:
            return

        visible_top = self.scroll
        visible_bottom = self.scroll + self.viewport_height

        for command in self.display_list:
            if command.bottom < visible_top:
                continue
            if command.top > visible_bottom:
                continue
            command.draw(painter, self.scroll)

    def follow_link_at(self, x: int, y: int) -> bool:
        if self.document is None:
            return False

        target_node = self._hit_test(x, y + self.scroll)
        if target_node is None:
            return False

        node: Node | None = target_node
        while node is not None:
            if isinstance(node, Element) and node.tag == "a":
                href = node.attributes.get("href")
                if href:
                    self.open(self.current_url.resolve(href), add_history=True)
                    return True
            node = node.parent

        return False

    def _hit_test(self, x: int, y: int) -> Node | None:
        if self.document is None:
            return None

        hits: list[Node] = []
        for item in layout_to_list(self.document, []):
            node = getattr(item, "node", None)
            if node is None:
                continue

            item_x = getattr(item, "x", None)
            item_y = getattr(item, "y", None)
            item_w = getattr(item, "width", None)
            item_h = getattr(item, "height", None)
            if None in {item_x, item_y, item_w, item_h}:
                continue

            if item_w <= 0 or item_h <= 0:
                continue

            if item_x <= x < item_x + item_w and item_y <= y < item_y + item_h:
                hits.append(node)

        if not hits:
            return None
        return hits[-1]

    def can_go_back(self) -> bool:
        return self.history_index > 0

    def can_go_forward(self) -> bool:
        return self.history_index + 1 < len(self.history)

    def back(self) -> bool:
        if not self.can_go_back():
            return False
        self.history_index -= 1
        self._load(self.history[self.history_index], add_history=False)
        return True

    def forward(self) -> bool:
        if not self.can_go_forward():
            return False
        self.history_index += 1
        self._load(self.history[self.history_index], add_history=False)
        return True

    def reload(self) -> None:
        self._load(self.current_url, add_history=False)

    def go_home(self) -> None:
        self.open(self.home_url, add_history=True)
