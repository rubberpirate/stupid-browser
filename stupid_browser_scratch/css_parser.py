from __future__ import annotations

from dataclasses import dataclass
import re

from .dom import Element, Node

_COMMENT_RE = re.compile(r"/\*.*?\*/", flags=re.S)
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", flags=re.S)


@dataclass(frozen=True)
class SimpleSelector:
    tag: str | None = None
    id_name: str | None = None
    classes: tuple[str, ...] = ()

    @property
    def specificity(self) -> tuple[int, int, int]:
        tag_count = 1 if self.tag is not None else 0
        return (1 if self.id_name else 0, len(self.classes), tag_count)

    def matches(self, node: Node) -> bool:
        if not isinstance(node, Element):
            return False

        if self.tag is not None and node.tag != self.tag:
            return False

        if self.id_name is not None and node.attributes.get("id") != self.id_name:
            return False

        if self.classes:
            present = set(node.attributes.get("class", "").split())
            for klass in self.classes:
                if klass not in present:
                    return False

        return True


@dataclass(frozen=True)
class DescendantSelector:
    parts: tuple[SimpleSelector, ...]

    @property
    def specificity(self) -> tuple[int, int, int]:
        ids = 0
        classes = 0
        tags = 0
        for part in self.parts:
            ids += part.specificity[0]
            classes += part.specificity[1]
            tags += part.specificity[2]
        return (ids, classes, tags)

    def matches(self, node: Node) -> bool:
        if not self.parts:
            return False
        if not self.parts[-1].matches(node):
            return False

        current = node.parent
        for part in reversed(self.parts[:-1]):
            while current is not None and not part.matches(current):
                current = current.parent
            if current is None:
                return False
            current = current.parent

        return True


@dataclass
class CSSRule:
    selector: DescendantSelector
    declarations: dict[str, str]
    order: int


def parse_stylesheet(source: str) -> list[CSSRule]:
    cleaned = _COMMENT_RE.sub("", source or "")
    rules: list[CSSRule] = []
    order = 0

    for match in _RULE_RE.finditer(cleaned):
        selectors_text = match.group(1)
        declarations = parse_declarations(match.group(2))
        if not declarations:
            continue

        for selector_text in selectors_text.split(","):
            selector = parse_selector(selector_text.strip())
            if selector is None:
                continue
            rules.append(CSSRule(selector, declarations.copy(), order))
            order += 1

    return rules


def parse_declarations(body: str) -> dict[str, str]:
    declarations: dict[str, str] = {}

    for part in body.split(";"):
        if ":" not in part:
            continue
        prop, value = part.split(":", 1)
        prop = prop.strip().lower()
        value = " ".join(value.strip().split())
        if not prop or not value:
            continue
        declarations[prop] = value

    return declarations


def parse_selector(text: str) -> DescendantSelector | None:
    if not text:
        return None

    parts: list[SimpleSelector] = []
    for token in text.split():
        simple = parse_simple_selector(token)
        if simple is None:
            return None
        parts.append(simple)

    if not parts:
        return None
    return DescendantSelector(tuple(parts))


def parse_simple_selector(token: str) -> SimpleSelector | None:
    if not token:
        return None

    i = 0
    tag_chars: list[str] = []
    while i < len(token) and token[i] not in ".#":
        tag_chars.append(token[i])
        i += 1

    tag = "".join(tag_chars).strip().lower() if tag_chars else None
    if tag == "*":
        tag = None

    id_name: str | None = None
    classes: list[str] = []

    while i < len(token):
        if token[i] not in ".#":
            return None

        marker = token[i]
        i += 1
        start = i
        while i < len(token) and (token[i].isalnum() or token[i] in "-_"):
            i += 1

        if start == i:
            return None

        value = token[start:i]
        if marker == "#":
            id_name = value
        else:
            classes.append(value)

    return SimpleSelector(tag=tag, id_name=id_name, classes=tuple(classes))
