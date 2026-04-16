# Stupid Browser Scratch

A clean-room browser project built from scratch in Python, inspired by browser.engineering.

## Features

- Loads pages over `http`, `https`, `file`, and `data` URLs
- Parses HTML into a DOM tree
- Parses CSS (tag, class, id, descendant selectors)
- Applies CSS cascade and inheritance
- Lays out block and inline content, including basic `<pre>` handling
- Renders styled text and backgrounds with a PySide6 custom paint view
- Clickable links and keyboard/mouse scrolling
- Tabbed chrome UI with back, forward, reload, home, address bar, and go controls
- Built-in search-style home page (`about:home`) with direct URL/query input.

## Run

```bash
cd stupid_browser_scratch
./start_browser.sh
```

You can also open a specific page:

```bash
./start_browser.sh https://browser.engineering/
```

To load a local file:

```bash
./start_browser.sh file:///absolute/path/to/file.html
```

A sample page is available at `samples/welcome.html`.
