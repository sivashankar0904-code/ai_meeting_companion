from __future__ import annotations

import signal
import sys
from typing import Callable, Sequence
from uuid import UUID

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from ai_meeting_companion.config import Settings
from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.orchestrator import Orchestrator
from ai_meeting_companion.memory.session_memory import SessionMemory
from ai_meeting_companion.session.store import SessionStore
from ai_meeting_companion.ui.forwarder import BusForwarder
from ai_meeting_companion.ui.hotkeys import start_hotkeys
from ai_meeting_companion.ui.overlay import OverlayController, OverlayWindow


def run_overlay(
    settings: Settings,
    store: SessionStore,
    build_agents: Callable[[Bus, SessionMemory], Sequence[BaseAgent]],
    title: str | None = None,
) -> UUID:
    """Run one session with the overlay as the UI. Blocks until the overlay is quit."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # hiding the overlay (hotkey) must not end the program
    controller = OverlayController()
    window = OverlayWindow(
        controller,
        opacity=settings.overlay_opacity,
        hide_from_capture=settings.overlay_hide_from_capture,
    )

    def agents(bus: Bus, memory: SessionMemory) -> list[BaseAgent]:
        return [*build_agents(bus, memory), BusForwarder(bus, controller.event_received.emit)]

    orch = Orchestrator(store, agents, title=title)
    window.set_publisher(orch.bus.publish)

    controller.quit_requested.connect(app.quit)
    # Let Ctrl+C in the terminal quit cleanly: Python only runs signal handlers when the interpreter runs.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    keepalive = QTimer()
    keepalive.timeout.connect(lambda: None)
    keepalive.start(200)

    hotkeys = start_hotkeys(
        {
            settings.overlay_toggle_hotkey: controller.toggle_visibility.emit,
            settings.overlay_clickthrough_hotkey: controller.toggle_click_through.emit,
            settings.overlay_focus_hotkey: controller.focus_input.emit,
            settings.suggest_hotkey: controller.suggest_requested.emit,
            settings.overlay_quit_hotkey: controller.quit_requested.emit,
        }
    )

    thread_id = orch.start()
    window.show()
    try:
        app.exec()
    finally:
        print("\nStopping and saving the session...", flush=True)
        hotkeys.stop()
        orch.stop()
        window.close()
    return thread_id
