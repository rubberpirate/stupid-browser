from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from urllib.parse import quote_plus, urlparse

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    DEFAULT_HOME,
    DEFAULT_SEARCH_TEMPLATE,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SCROLL_STEP,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .tab import Tab


@dataclass
class BrowserTabState:
    engine: Tab
    title: str = "welcome"
    is_home: bool = True


class HomePage(QWidget):
    submitted = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("home-page")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 40, 24, 40)
        root.setSpacing(24)

        root.addStretch(2)

        self.logo = QLabel("STUPID\nBROWSER")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setObjectName("home-logo")
        root.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.group_label = QLabel("Group 13")
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setObjectName("group-label")
        root.addWidget(self.group_label, alignment=Qt.AlignmentFlag.AlignCenter)

        search_shell = QFrame()
        search_shell.setObjectName("search-shell")
        search_layout = QHBoxLayout(search_shell)
        search_layout.setContentsMargins(16, 8, 12, 8)
        search_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search-input")
        self.search_input.setPlaceholderText("Search or enter URL")
        self.search_input.returnPressed.connect(self._emit_submission)
        search_layout.addWidget(self.search_input)

        self.search_button = QToolButton()
        self.search_button.setObjectName("search-button")
        self.search_button.setText("⌕")
        self.search_button.clicked.connect(self._emit_submission)
        search_layout.addWidget(self.search_button)

        root.addWidget(search_shell, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch(3)

    def _emit_submission(self) -> None:
        self.submitted.emit(self.search_input.text())

    def focus_search(self) -> None:
        self.search_input.setFocus(Qt.FocusReason.OtherFocusReason)


class BrowserView(QWidget):
    link_activated = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._tab: Tab | None = None

    def set_tab(self, tab: Tab | None) -> None:
        self._tab = tab
        if self._tab is not None:
            self._tab.set_viewport(max(200, self.width()), max(120, self.height()))
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#d0d1d5"))

        if self._tab is not None:
            self._tab.draw(painter)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._tab is not None:
            self._tab.set_viewport(max(200, event.size().width()), max(120, event.size().height()))
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._tab is not None
            and self._tab.follow_link_at(int(event.position().x()), int(event.position().y()))
        ):
            self.link_activated.emit()
            self.update()
            return

        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._tab is None:
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        if delta > 0:
            self._tab.scroll_by(-SCROLL_STEP)
        elif delta < 0:
            self._tab.scroll_by(SCROLL_STEP)

        self.update()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._tab is None:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_Up:
            self._tab.scroll_by(-SCROLL_STEP)
        elif key == Qt.Key.Key_Down:
            self._tab.scroll_by(SCROLL_STEP)
        elif key == Qt.Key.Key_PageUp:
            self._tab.scroll_by(-3 * SCROLL_STEP)
        elif key == Qt.Key.Key_PageDown:
            self._tab.scroll_by(3 * SCROLL_STEP)
        elif key == Qt.Key.Key_Home:
            self._tab.scroll = 0
        elif key == Qt.Key.Key_End:
            self._tab.scroll = self._tab.max_scroll
        else:
            super().keyPressEvent(event)
            return

        self.update()


class BrowserGUI(QMainWindow):
    def __init__(self, start_url: str, home_url: str = DEFAULT_HOME):
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        super().__init__()

        self.home_url = home_url
        self.tabs: list[BrowserTabState] = []

        self.setWindowTitle("Stupid Browser")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self._build_ui()
        self._bind_events()
        self._add_tab(switch_to=True)
        self._load_from_text(start_url, add_history=True)

    def _build_ui(self) -> None:
        shell = QWidget()
        self.setCentralWidget(shell)

        root = QVBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        chrome = QFrame()
        chrome.setObjectName("chrome")
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(6, 6, 6, 6)
        chrome_layout.setSpacing(4)

        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.setSpacing(4)

        app_dot = QLabel()
        app_dot.setFixedSize(20, 20)
        app_dot.setObjectName("app-dot")
        tab_row.addWidget(app_dot)

        self.tab_bar = QTabBar()
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setMovable(False)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setUsesScrollButtons(True)
        tab_row.addWidget(self.tab_bar, 1)

        self.new_tab_button = QPushButton("+")
        self.new_tab_button.setObjectName("new-tab")
        self.new_tab_button.setFixedSize(24, 24)
        tab_row.addWidget(self.new_tab_button)

        chrome_layout.addLayout(tab_row)

        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(8)

        self.back_button = self._create_nav_button("←", "Back")
        self.forward_button = self._create_nav_button("→", "Forward")
        self.reload_button = self._create_nav_button("⟳", "Reload")
        self.home_button = self._create_nav_button("⌂", "Home")

        nav_row.addWidget(self.back_button)
        nav_row.addWidget(self.forward_button)
        nav_row.addWidget(self.reload_button)
        nav_row.addWidget(self.home_button)

        self.address_bar = QLineEdit()
        self.address_bar.setObjectName("address-bar")
        self.address_bar.setPlaceholderText("Search or enter URL")
        nav_row.addWidget(self.address_bar, 1)

        chrome_layout.addLayout(nav_row)

        root.addWidget(chrome)

        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.browser_view = BrowserView()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.browser_view)
        root.addWidget(self.stack, 1)

        self.setStyleSheet(
            """
            QMainWindow {
                background: #d0d1d5;
            }
            #chrome {
                background: #2b2a33;
            }
            #app-dot {
                border-radius: 10px;
                background: #45bea7;
                margin-left: 4px;
            }
            QTabBar::tab {
                background: #42414d;
                color: #fbfbfe;
                border-radius: 6px;
                padding: 6px 12px;
                margin-right: 4px;
                font-size: 13px;
                min-width: 120px;
                max-width: 200px;
            }
            QTabBar::tab:selected {
                background: #52525e;
            }
            QTabBar::close-button {
                image: none;
                subcontrol-position: right;
                width: 12px;
                height: 12px;
                margin-left: 4px;
                background: #8f8f9d;
                border-radius: 6px;
            }
            QTabBar::close-button:hover {
                background: #d7d7db;
            }
            #new-tab {
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 500;
                color: #f0f1f3;
                background: transparent;
            }
            #new-tab:hover {
                background: #42414d;
            }
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 4px;
                color: #fbfbfe;
                font-size: 16px;
                background: transparent;
                min-width: 28px;
            }
            QToolButton:hover {
                background: #42414d;
            }
            QToolButton:disabled {
                color: #737986;
            }
            #address-bar {
                border: none;
                border-radius: 14px;
                background: #1c1b22;
                padding: 4px 14px;
                color: #fbfbfe;
                font-size: 13px;
                margin-left: 4px;
                margin-right: 4px;
            }
            #address-bar:focus {
                border: 2px solid #00ddff;
                background: #2b2a33;
            }
            #go-button {
                display: none;
            }
            #home-page {
                background: #2b2a33;
            }
            #home-logo {
                color: #fbfbfe;
                font-size: 56px;
                font-family: inherit;
                font-weight: 700;
                letter-spacing: 2px;
            }
            #group-label {
                color: #8f8f9d;
                font-size: 24px;
                font-weight: 500;
            }
            #search-shell {
                background: #42414d;
                border: none;
                border-radius: 20px;
                min-width: 500px;
                max-width: 800px;
            }
            #search-input {
                border: none;
                background: transparent;
                color: #fbfbfe;
                font-size: 18px;
                padding: 8px 12px;
            }
            #search-button {
                border: none;
                background: transparent;
                color: #fbfbfe;
                font-size: 24px;
            }
            """
        )

    def _create_nav_button(self, glyph: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(glyph)
        button.setToolTip(tooltip)
        return button

    def _bind_events(self) -> None:
        self.new_tab_button.clicked.connect(self._on_new_tab)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)

        self.back_button.clicked.connect(self.on_back)
        self.forward_button.clicked.connect(self.on_forward)
        self.reload_button.clicked.connect(self.on_reload)
        self.home_button.clicked.connect(self.on_home)

        self.address_bar.returnPressed.connect(self.on_go)
        self.home_page.submitted.connect(lambda text: self._load_from_text(text, add_history=True))
        self.browser_view.link_activated.connect(self._on_link_activated)

    def _viewport_size(self) -> tuple[int, int]:
        width = self.browser_view.width() or WINDOW_WIDTH
        height = self.browser_view.height() or (WINDOW_HEIGHT - 160)
        return (max(220, width), max(140, height))

    def _add_tab(self, switch_to: bool) -> None:
        viewport_width, viewport_height = self._viewport_size()
        engine = Tab(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            home_url=self.home_url,
        )

        state = BrowserTabState(engine=engine)
        self.tabs.append(state)

        tab_index = self.tab_bar.addTab(state.title)
        if switch_to:
            self.tab_bar.setCurrentIndex(tab_index)

    def _current_index(self) -> int:
        return self.tab_bar.currentIndex()

    def _current_state(self) -> BrowserTabState:
        return self.tabs[self._current_index()]

    def _tab_title(self, url: str) -> str:
        parsed = urlparse(url)

        if parsed.hostname:
            host = parsed.hostname
            if host.startswith("www."):
                host = host[4:]
            return host[:18]

        if parsed.scheme == "file":
            name = Path(parsed.path).name
            return name[:18] if name else "file"

        return parsed.scheme[:18] if parsed.scheme else "page"

    def _normalize_input(self, raw: str) -> str | None:
        text = raw.strip()
        if not text:
            return None

        lower = text.lower()
        if lower in {"about:home", "home"}:
            return "about:home"

        maybe_path = Path(text).expanduser()
        if maybe_path.exists():
            return maybe_path.resolve().as_uri()

        if lower.startswith(("http://", "https://", "file://", "data:")) or "://" in text:
            return text

        if " " not in text and (
            "." in text
            or text.startswith("localhost")
            or text.startswith("127.")
            or text.startswith("[::1]")
        ):
            return f"https://{text}"

        return DEFAULT_SEARCH_TEMPLATE.format(query=quote_plus(text))

    def _sync_ui_to_state(self) -> None:
        state = self._current_state()

        if state.is_home:
            self.stack.setCurrentWidget(self.home_page)
            self.browser_view.set_tab(None)
            self.address_bar.clear()
            self.home_page.focus_search()
        else:
            self.stack.setCurrentWidget(self.browser_view)
            self.browser_view.set_tab(state.engine)
            self.address_bar.setText(str(state.engine.current_url))
            self.browser_view.setFocus(Qt.FocusReason.OtherFocusReason)

        self.back_button.setEnabled(state.engine.can_go_back())
        self.forward_button.setEnabled(state.engine.can_go_forward())
        self.reload_button.setEnabled(not state.is_home)

    def _load_from_text(self, raw: str, add_history: bool) -> None:
        normalized = self._normalize_input(raw)
        if normalized is None:
            return

        state = self._current_state()
        tab_index = self._current_index()

        if normalized == "about:home":
            state.is_home = True
            state.title = "welcome"
            self.tab_bar.setTabText(tab_index, state.title)
            self._sync_ui_to_state()
            return

        state.engine.open(normalized, add_history=add_history)
        state.is_home = False
        state.title = self._tab_title(str(state.engine.current_url))
        self.tab_bar.setTabText(tab_index, state.title)

        self._sync_ui_to_state()
        self.browser_view.update()

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.tabs):
            return
        self._sync_ui_to_state()

    def _on_tab_close_requested(self, index: int) -> None:
        if len(self.tabs) <= 1:
            return

        self.tabs.pop(index)
        self.tab_bar.removeTab(index)

        next_index = min(index, len(self.tabs) - 1)
        self.tab_bar.setCurrentIndex(next_index)

    def _on_new_tab(self) -> None:
        self._add_tab(switch_to=True)
        state = self._current_state()
        state.is_home = True
        state.title = "welcome"
        self.tab_bar.setTabText(self._current_index(), state.title)
        self._sync_ui_to_state()

    def _on_link_activated(self) -> None:
        state = self._current_state()
        state.is_home = False
        state.title = self._tab_title(str(state.engine.current_url))
        self.tab_bar.setTabText(self._current_index(), state.title)
        self._sync_ui_to_state()

    def on_go(self) -> None:
        self._load_from_text(self.address_bar.text(), add_history=True)

    def on_back(self) -> None:
        state = self._current_state()
        if not state.engine.back():
            return

        state.is_home = False
        state.title = self._tab_title(str(state.engine.current_url))
        self.tab_bar.setTabText(self._current_index(), state.title)
        self._sync_ui_to_state()
        self.browser_view.update()

    def on_forward(self) -> None:
        state = self._current_state()
        if not state.engine.forward():
            return

        state.is_home = False
        state.title = self._tab_title(str(state.engine.current_url))
        self.tab_bar.setTabText(self._current_index(), state.title)
        self._sync_ui_to_state()
        self.browser_view.update()

    def on_reload(self) -> None:
        state = self._current_state()
        if state.is_home:
            return

        state.engine.reload()
        self._sync_ui_to_state()
        self.browser_view.update()

    def on_home(self) -> None:
        state = self._current_state()
        state.is_home = True
        state.title = "welcome"
        self.tab_bar.setTabText(self._current_index(), state.title)
        self._sync_ui_to_state()

    def run(self) -> int:
        self.show()
        return self.qt_app.exec()
