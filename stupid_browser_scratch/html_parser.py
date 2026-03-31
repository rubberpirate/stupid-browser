from __future__ import annotations

import re

from .constants import SELF_CLOSING_TAGS
from .dom import Element, Text

ATTR_RE = re.compile(
    r"""([a-zA-Z_:][a-zA-Z0-9_:\-.]*)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+)))?"""
)

_HEAD_ALLOWED = {"title", "meta", "link", "style", "base"}


class HTMLParser:
    def __init__(self, source: str):
        self.source = source
        self.root = Element("html", {})
        self.body: Element | None = None
        self.head: Element | None = None
        self.stack: list[Element] = [self.root]

    def parse(self) -> Element:
        i = 0
        text_buffer: list[str] = []

        while i < len(self.source):
            if self.source.startswith("<!--", i):
                self._flush_text(text_buffer)
                end = self.source.find("-->", i + 4)
                if end == -1:
                    break
                i = end + 3
                continue

            ch = self.source[i]
            if ch == "<":
                close = self.source.find(">", i + 1)
                if close == -1:
                    text_buffer.append(ch)
                    i += 1
                    continue

                self._flush_text(text_buffer)
                self._add_tag(self.source[i + 1 : close].strip())
                i = close + 1
                continue

            text_buffer.append(ch)
            i += 1

        self._flush_text(text_buffer)
        return self.root

    def _flush_text(self, text_buffer: list[str]) -> None:
        if not text_buffer:
            return

        text = "".join(text_buffer)
        text_buffer.clear()

        if not text:
            return
        if text.isspace() and not self._inside_pre(self.stack[-1]):
            return

        if self.stack[-1] is self.root:
            self._ensure_body_open()

        self.stack[-1].append_child(Text(text, self.stack[-1]))

    def _inside_pre(self, node: Element) -> bool:
        current: Element | None = node
        while current is not None:
            if current.tag == "pre":
                return True
            parent = current.parent
            current = parent if isinstance(parent, Element) else None
        return False

    def _parse_tag(
        self, content: str
    ) -> tuple[str, dict[str, str], bool, bool] | None:
        if not content:
            return None

        if content.startswith("!"):
            return None

        if content.startswith("/"):
            tag = content[1:].strip().lower()
            if not tag:
                return None
            return tag, {}, True, False

        self_closing = content.endswith("/")
        if self_closing:
            content = content[:-1].rstrip()

        parts = content.split(None, 1)
        tag = parts[0].lower()
        attr_text = parts[1] if len(parts) == 2 else ""

        attrs: dict[str, str] = {}
        for match in ATTR_RE.finditer(attr_text):
            key = match.group(1).lower()
            value = match.group(2) or match.group(3) or match.group(4) or ""
            attrs[key] = value

        return tag, attrs, False, self_closing or tag in SELF_CLOSING_TAGS

    def _add_tag(self, content: str) -> None:
        parsed = self._parse_tag(content)
        if parsed is None:
            return

        tag, attrs, is_closing, self_closing = parsed
        if is_closing:
            self._close_tag(tag)
        else:
            self._open_tag(tag, attrs, self_closing)

    def _open_tag(
        self, tag: str, attrs: dict[str, str], self_closing: bool
    ) -> None:
        if tag == "html":
            self.root.attributes.update(attrs)
            return

        if tag == "head":
            if self.body is not None:
                return
            if self.head is None:
                self.head = Element("head", attrs, self.root)
                self.root.append_child(self.head)
            else:
                self.head.attributes.update(attrs)
            if self.head not in self.stack:
                self.stack.append(self.head)
            return

        if tag == "body":
            if self.stack[-1].tag == "head":
                self.stack.pop()
            if self.body is None:
                self.body = Element("body", attrs, self.root)
                self.root.append_child(self.body)
            else:
                self.body.attributes.update(attrs)
            if self.body not in self.stack:
                self.stack.append(self.body)
            return

        if self.stack[-1].tag == "head" and tag not in _HEAD_ALLOWED:
            self.stack.pop()

        if self.stack[-1] is self.root and tag not in _HEAD_ALLOWED:
            self._ensure_body_open()

        if self.stack[-1] is self.root and tag in _HEAD_ALLOWED:
            if self.head is None:
                self.head = Element("head", {}, self.root)
                self.root.append_child(self.head)
            if self.head not in self.stack:
                self.stack.append(self.head)

        parent = self.stack[-1]
        node = Element(tag, attrs, parent)
        parent.append_child(node)

        if not self_closing:
            self.stack.append(node)

    def _close_tag(self, tag: str) -> None:
        if tag in {"html", "body"}:
            return

        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def _ensure_body_open(self) -> None:
        if self.stack[-1].tag == "head":
            self.stack.pop()

        if self.body is None:
            self.body = Element("body", {}, self.root)
            self.root.append_child(self.body)

        if self.body not in self.stack:
            self.stack.append(self.body)
