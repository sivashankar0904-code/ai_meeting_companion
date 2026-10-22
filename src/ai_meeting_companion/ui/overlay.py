from __future__ import annotations

import json
from html import escape
from typing import Callable

from PyQt6.QtCore import QObject, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizeGrip,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ai_meeting_companion.core.events import (
    ERROR,
    LLM_RESPONSE,
    SCREEN_TEXT,
    STATUS,
    SUGGEST_REQUEST,
    TRANSCRIPT,
    USER_MESSAGE,
    Event,
)
from ai_meeting_companion import config
from ai_meeting_companion.ui import win32

WIDTH, HEIGHT, MARGIN = 460, 580, 24
POSITION_FILE = "overlay_position.json"
HEARD_CHARS = 220

AGENT_COLORS = {"conversor": "#7aa2f7", "screen_analyzer": "#9ece6a", "chat": "#bb9af7"}
MUTED, ERROR_COLOR = "#8b90a0", "#f7768e"

STYLE = """
#panel { background: rgba(22, 24, 32, 235); border: 1px solid rgba(255,255,255,40); border-radius: 12px; }
QLabel { color: #c9cddb; font-family: 'Segoe UI'; font-size: 9pt; }
#title { color: #e6e8f2; font-weight: 600; font-size: 10pt; }
#note { color: #8b90a0; }
QTextBrowser { background: transparent; border: none; color: #e6e8f2; font-family: 'Segoe UI'; font-size: 10pt;
               selection-background-color: #3d59a1; }
QLineEdit { background: rgba(255,255,255,18); border: 1px solid rgba(255,255,255,40); border-radius: 6px;
            color: #e6e8f2; padding: 6px 8px; font-family: 'Segoe UI'; font-size: 10pt; }
QPushButton { background: rgba(255,255,255,18); color: #c9cddb; border: none; border-radius: 5px;
              padding: 3px 8px; font-family: 'Segoe UI'; font-size: 8pt; }
QPushButton:hover { background: rgba(255,255,255,40); }
QPushButton:checked { background: #3d59a1; color: white; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,50); border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class OverlayController(QObject):
    """Thread-safe entry points: emit these from any thread (agents, global hotkeys)."""

    event_received = pyqtSignal(object)
    toggle_visibility = pyqtSignal()
    toggle_click_through = pyqtSignal()
    focus_input = pyqtSignal()
    suggest_requested = pyqtSignal()
    quit_requested = pyqtSignal()


class OverlayWindow(QWidget):
    """Always-on-top, frameless assistant panel that is excluded from screen capture."""

    def __init__(
        self,
        controller: OverlayController,
        *,
        publish: Callable[[Event], None] | None = None,
        opacity: float = 0.94,
        hide_from_capture: bool = True,
    ) -> None:
        super().__init__()
        self.controller = controller
        self._publish = publish
        self._hide_from_capture = hide_from_capture
        self._click_through = False
        self.capture_hidden = False

        self.setWindowTitle("Meeting Companion")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(opacity)
        self.setStyleSheet(STYLE)
        self.resize(WIDTH, HEIGHT)
        self._drag_offset: QPoint | None = None
        self._position_file = config.PROJECT_ROOT / POSITION_FILE
        if not self._restore_position():
            self._place_top_right()
        self._build()

        controller.event_received.connect(self.on_event)
        controller.toggle_visibility.connect(self.toggle_visibility)
        controller.toggle_click_through.connect(self.toggle_click_through)
        controller.focus_input.connect(self.focus_input)
        controller.suggest_requested.connect(self.request_suggestion)

    # -- layout ---------------------------------------------------------
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        panel = QFrame(self)
        panel.setObjectName("panel")
        outer.addWidget(panel)
        col = QVBoxLayout(panel)
        col.setContentsMargins(12, 8, 12, 10)
        col.setSpacing(6)

        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Meeting Companion")
        title.setObjectName("title")
        self.capture_label = QLabel("")
        self.suggest_button = QPushButton("Suggest")
        self.suggest_button.setToolTip("Send what was heard to the Conversor for a suggested answer")
        self.suggest_button.clicked.connect(lambda _=False: self.controller.suggest_requested.emit())
        self.click_button = QPushButton("Click-through")
        self.click_button.setCheckable(True)
        self.click_button.setToolTip("Let mouse clicks pass through the overlay (toggle with the hotkey)")
        self.click_button.clicked.connect(lambda _=False: self.set_click_through(self.click_button.isChecked()))
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)
        close = QPushButton("Quit")
        close.clicked.connect(self.controller.quit_requested.emit)
        for w in (title, self.capture_label):
            row.addWidget(w)
        row.addStretch(1)
        for b in (self.suggest_button, self.click_button, clear, close):
            row.addWidget(b)
        col.addWidget(header)

        self.heard = QLabel("Starting...")
        self.heard.setObjectName("note")
        self.heard.setWordWrap(True)
        self.screen_note = QLabel("")
        self.screen_note.setObjectName("note")
        self.screen_note.setWordWrap(True)
        col.addWidget(self.heard)
        col.addWidget(self.screen_note)

        self.feed = QTextBrowser()
        self.feed.setOpenExternalLinks(False)
        col.addWidget(self.feed, 1)

        bottom = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask anything, press Enter to send")
        self.input.returnPressed.connect(self._send)
        bottom.addWidget(self.input, 1)
        bottom.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        col.addLayout(bottom)

    def _place_top_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.right() - WIDTH - MARGIN, area.top() + MARGIN)

    # -- dragging: press and drag anywhere that is not a button, the feed or the input box ----------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_offset is not None:
            self._drag_offset = None
            self._save_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _save_position(self) -> None:
        try:
            self._position_file.write_text(json.dumps({"x": self.x(), "y": self.y()}), encoding="utf-8")
        except OSError:
            pass  # remembering the position is a convenience, never an error

    def _restore_position(self) -> bool:
        """Move to the last saved spot if it is still on a connected screen."""
        try:
            data = json.loads(self._position_file.read_text(encoding="utf-8"))
            point = QPoint(int(data["x"]), int(data["y"]))
        except (OSError, ValueError, KeyError, TypeError):
            return False
        for screen in QGuiApplication.screens():
            if screen.availableGeometry().contains(point + QPoint(40, 20)):  # title area stays reachable
                self.move(point)
                return True
        return False

    def set_publisher(self, publish: Callable[[Event], None]) -> None:
        self._publish = publish

    def closeEvent(self, event) -> None:
        """Closing the overlay (Alt+F4, taskkill, Windows shutdown) quits the app so the session is saved.
        Hiding it is a separate action (the show/hide hotkey)."""
        self.controller.quit_requested.emit()
        super().closeEvent(event)

    # -- capture exclusion ------------------------------------------------
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.apply_capture_exclusion()

    def apply_capture_exclusion(self) -> None:
        """Call whenever the native window may have been recreated (every show)."""
        if not self._hide_from_capture:
            self.capture_hidden = False
        else:
            self.capture_hidden = win32.set_capture_excluded(int(self.winId()), True)
        if self._hide_from_capture and self.capture_hidden:
            self.capture_label.setText("hidden from capture")
            self.capture_label.setStyleSheet("color: #9ece6a;")
        elif self._hide_from_capture:
            self.capture_label.setText("VISIBLE to screen share")
            self.capture_label.setStyleSheet("color: #f7768e;")
        else:
            self.capture_label.setText("capture exclusion off")
            self.capture_label.setStyleSheet("color: #8b90a0;")

    # -- visibility / interaction -------------------------------------------
    def toggle_visibility(self) -> None:
        self.hide() if self.isVisible() else self.show()

    def toggle_click_through(self) -> None:
        self.set_click_through(not self._click_through)

    def set_click_through(self, on: bool) -> None:
        self._click_through = on
        self.click_button.setChecked(on)
        geometry = self.geometry()
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, on)
        self.show()  # changing window flags hides the window; showEvent re-applies capture exclusion
        self.setGeometry(geometry)

    def focus_input(self) -> None:
        if self._click_through:
            self.set_click_through(False)
        self.show()
        self.activateWindow()
        self.raise_()
        self.input.setFocus()

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        if self._publish is not None:
            self._publish(Event(kind=USER_MESSAGE, source="overlay", payload={"text": text}))

    def request_suggestion(self) -> None:
        if self._publish is not None:
            self._publish(Event(kind=SUGGEST_REQUEST, source="overlay", payload={"text": ""}))

    def clear(self) -> None:
        self.feed.clear()
        self.screen_note.setText("")

    # -- rendering ----------------------------------------------------------
    def on_event(self, event: Event) -> None:
        text = event.text
        if event.kind == STATUS:
            self.heard.setText(text)
        elif event.kind == TRANSCRIPT:
            channel = event.payload.get("channel")
            shown = text if len(text) <= HEARD_CHARS else "..." + text[-HEARD_CHARS:]
            self.heard.setText(f"Heard{f' [{channel}]' if channel else ''}: {shown}")
        elif event.kind == SCREEN_TEXT:
            self.screen_note.setText(f"Screen captured ({len(text)} characters), analysing...")
        elif event.kind == USER_MESSAGE:
            self._append("You", MUTED, text)
        elif event.kind == LLM_RESPONSE:
            agent = event.payload.get("agent") or event.source
            if agent == "screen_analyzer":
                self.screen_note.setText("")
            latency = event.payload.get("latency_ms")
            meta = " · ".join(
                part for part in (agent, event.payload.get("model"), f"{latency / 1000:.1f}s" if latency else None) if part
            )
            self._append(meta, AGENT_COLORS.get(agent, "#c9cddb"), text)
        elif event.kind == ERROR:
            self._append(f"error · {event.payload.get('agent') or event.source}", ERROR_COLOR, text)

    def add_note(self, header: str, markdown: str, warning: bool = False) -> None:
        """A message from the app itself (not an agent), e.g. which context files were loaded."""
        self._append(header, ERROR_COLOR if warning else MUTED, markdown)

    def _append(self, header: str, color: str, markdown: str) -> None:
        bar = self.feed.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        doc = QTextDocument()
        doc.setMarkdown(markdown)
        cursor = self.feed.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.feed.document().isEmpty():
            cursor.insertBlock()  # each entry starts on its own paragraph
        cursor.setBlockFormat(QTextBlockFormat())
        cursor.setCharFormat(QTextCharFormat())
        cursor.insertHtml(f'<span style="color:{color}; font-weight:600;">{escape(header)}</span>')
        cursor.insertBlock()
        cursor.setBlockFormat(QTextBlockFormat())
        cursor.setCharFormat(QTextCharFormat())  # do not inherit the header colour
        cursor.insertHtml(doc.toHtml())
        if at_bottom:
            bar.setValue(bar.maximum())
