from __future__ import annotations

from typing import Iterator


class Node:
    def __init__(self, parent: Node | None = None):
        self.parent = parent
        self.children: list[Node] = []
        self.style: dict[str, str] = {}

    def append_child(self, child: Node) -> None:
        child.parent = self
        self.children.append(child)


class Text(Node):
    def __init__(self, text: str, parent: Node | None = None):
        super().__init__(parent)
        self.text = text

    def __repr__(self) -> str:
        return f"Text({self.text!r})"


class Element(Node):
    def __init__(
        self,
        tag: str,
        attributes: dict[str, str] | None = None,
        parent: Node | None = None,
    ):
        super().__init__(parent)
        self.tag = tag.lower()
        self.attributes = attributes or {}

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.attributes.get(key, default)

    def __repr__(self) -> str:
        return f"Element(tag={self.tag!r}, attrs={self.attributes!r})"


def walk(node: Node) -> Iterator[Node]:
    yield node
    for child in node.children:
        yield from walk(child)


def text_content(node: Node) -> str:
    if isinstance(node, Text):
        return node.text
    return "".join(text_content(child) for child in node.children)


def find_ancestor(node: Node | None, tag: str) -> Element | None:
    while node is not None:
        if isinstance(node, Element) and node.tag == tag:
            return node
        node = node.parent
    return None
