from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import QPoint, QRect, QSize

# direction -> (column step, row step) on the 3x3 grid
STEPS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}


def _anchor(index: int, start: int, extent: int, size: int, margin: int) -> int:
    """Coordinate of grid line ``index`` (0 = near edge, 1 = centre, 2 = far edge) along one axis."""
    if index == 0:
        return start + margin
    if index == 2:
        return start + extent - size - margin
    return start + (extent - size) // 2


def anchor(area: QRect, size: QSize, margin: int, col: int, row: int) -> QPoint:
    return QPoint(
        _anchor(col, area.x(), area.width(), size.width(), margin),
        _anchor(row, area.y(), area.height(), size.height(), margin),
    )


def nearest_cell(pos: QPoint, area: QRect, size: QSize, margin: int) -> tuple[int, int]:
    """The grid cell closest to ``pos``, so stepping also works after a manual drag."""
    col = min(range(3), key=lambda c: abs(pos.x() - anchor(area, size, margin, c, 0).x()))
    row = min(range(3), key=lambda r: abs(pos.y() - anchor(area, size, margin, 0, r).y()))
    return col, row


def _neighbour(current: QRect, areas: Sequence[QRect], direction: str) -> QRect | None:
    """The closest other screen lying in ``direction`` that overlaps the current one on the other axis."""
    best: tuple[int, QRect] | None = None
    for other in areas:
        if other == current:
            continue
        if direction == "left" and other.right() < current.left() and other.top() <= current.bottom() and other.bottom() >= current.top():
            gap = current.left() - other.right()
        elif direction == "right" and other.left() > current.right() and other.top() <= current.bottom() and other.bottom() >= current.top():
            gap = other.left() - current.right()
        elif direction == "up" and other.bottom() < current.top() and other.left() <= current.right() and other.right() >= current.left():
            gap = current.top() - other.bottom()
        elif direction == "down" and other.top() > current.bottom() and other.left() <= current.right() and other.right() >= current.left():
            gap = other.top() - current.bottom()
        else:
            continue
        if best is None or gap < best[0]:
            best = (gap, other)
    return best[1] if best else None


def next_position(pos: QPoint, size: QSize, areas: Sequence[QRect], direction: str, margin: int) -> QPoint | None:
    """Where a window at ``pos`` goes after one step ``direction`` on the 3x3 grid of its screen.

    ``areas`` are the usable geometries of all screens. At the edge of a screen the window hops to
    the neighbouring screen in that direction (landing on its opposite edge, same row or column);
    with no neighbour it stays put (``None``)."""
    if direction not in STEPS or not areas:
        return None
    centre = pos + QPoint(size.width() // 2, size.height() // 2)
    area = next((a for a in areas if a.contains(centre)), None) or areas[0]
    col, row = nearest_cell(pos, area, size, margin)
    dc, dr = STEPS[direction]
    new_col, new_row = col + dc, row + dr
    if 0 <= new_col <= 2 and 0 <= new_row <= 2:
        return anchor(area, size, margin, new_col, new_row)
    other = _neighbour(area, areas, direction)
    if other is None:
        return None
    return anchor(other, size, margin, new_col % 3, new_row % 3)
