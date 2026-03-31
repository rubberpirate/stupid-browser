WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 720
MIN_WINDOW_HEIGHT = 520

HSTEP = 16
VSTEP = 18
SCROLL_STEP = 96

DEFAULT_HOME = "https://browser.engineering/"
DEFAULT_START_PAGE = "about:home"
DEFAULT_SEARCH_TEMPLATE = "https://duckduckgo.com/?q={query}"
MAX_REDIRECTS = 8

BLOCK_ELEMENTS = {
    "html",
    "body",
    "article",
    "section",
    "nav",
    "aside",
    "header",
    "footer",
    "main",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "div",
    "blockquote",
    "pre",
    "ul",
    "ol",
    "li",
    "table",
    "tr",
    "td",
    "th",
    "form",
}

SELF_CLOSING_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

HIDDEN_BY_DEFAULT = {
    "head",
    "title",
    "meta",
    "link",
    "script",
    "style",
}
