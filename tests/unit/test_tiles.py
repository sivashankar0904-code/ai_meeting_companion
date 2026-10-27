import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QRect, QSize

from ai_meeting_companion.ui.tiles import anchor, next_position

AREA = QRect(0, 0, 1920, 1040)
SIZE = QSize(460, 580)
M = 24


def pos(col, row, area=AREA):
    return anchor(area, SIZE, M, col, row)


def test_each_direction_steps_one_cell():
    assert next_position(pos(1, 1), SIZE, [AREA], "left", M) == pos(0, 1)
    assert next_position(pos(1, 1), SIZE, [AREA], "right", M) == pos(2, 1)
    assert next_position(pos(1, 1), SIZE, [AREA], "up", M) == pos(1, 0)
    assert next_position(pos(1, 1), SIZE, [AREA], "down", M) == pos(1, 2)


def test_edges_stay_put_without_neighbour():
    assert next_position(pos(0, 0), SIZE, [AREA], "left", M) is None
    assert next_position(pos(2, 2), SIZE, [AREA], "down", M) is None


def test_off_grid_position_snaps_to_nearest_then_steps():
    near_top_right = QPoint(AREA.width() - SIZE.width() - 40, 60)
    assert next_position(near_top_right, SIZE, [AREA], "down", M) == pos(2, 1)


def test_hops_to_neighbouring_screen():
    right = QRect(1920, 0, 1920, 1040)
    assert next_position(pos(2, 1), SIZE, [AREA, right], "right", M) == pos(0, 1, right)
    assert next_position(pos(0, 1, right), SIZE, [AREA, right], "left", M) == pos(2, 1)
    assert next_position(pos(2, 1, right), SIZE, [AREA, right], "right", M) is None


def test_overlay_moves_and_saves(tmp_path):
    from PyQt6.QtWidgets import QApplication

    from ai_meeting_companion.ui.overlay import OverlayController, OverlayWindow

    app = QApplication.instance() or QApplication([])  # noqa: F841 (must stay referenced)
    controller = OverlayController()
    window = OverlayWindow(controller)
    window._position_file = tmp_path / "pos.json"
    before = window.pos()
    controller.move_tile.emit("down")
    assert window.pos().y() > before.y()
    assert (tmp_path / "pos.json").exists()


def test_header_buttons_are_icons():
    from PyQt6.QtWidgets import QApplication, QPushButton

    from ai_meeting_companion.ui.overlay import OverlayController, OverlayWindow

    app = QApplication.instance() or QApplication([])  # noqa: F841
    window = OverlayWindow(OverlayController())
    buttons = window.findChildren(QPushButton)
    assert len(buttons) == 5
    assert all(b.text() == "" and not b.icon().isNull() and b.toolTip() for b in buttons)


def test_screenshot_request_triggers_capture():
    from PIL import Image

    from ai_meeting_companion.agents.perception.screen.agent import ScreenAgent
    from ai_meeting_companion.core.bus import Bus
    from ai_meeting_companion.core.events import SCREEN_TEXT, SCREENSHOT_REQUEST, Event

    bus = Bus()
    sub = bus.subscribe({SCREEN_TEXT})
    agent = ScreenAgent(bus, lambda: Image.new("RGB", (4, 4)), lambda _img: "two sum")
    agent.start()
    try:
        bus.publish(Event(kind=SCREENSHOT_REQUEST, source="test", payload={}))
        got = sub.get(timeout=3)
        assert got is not None and got.text == "two sum"
    finally:
        agent.stop()
