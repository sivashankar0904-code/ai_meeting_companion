from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

SIZE = 16  # logical pixels; drawn at 2x so the icons stay sharp on high-DPI screens


def _polygon(points: list[tuple[float, float]]) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in points])


def _draw(name: str, p: QPainter, color: QColor) -> None:
    pen = QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if name == "suggest":  # lightning bolt
        p.setBrush(color)
        p.drawPolygon(_polygon([(9.5, 1.5), (3.5, 9), (7.5, 9), (6.5, 14.5), (12.5, 7), (8.5, 7)]))
    elif name == "screenshot":  # camera
        body = QPainterPath()
        body.addRoundedRect(QRectF(2, 5, 12, 8.5), 1.8, 1.8)
        p.drawPath(body)
        p.drawPolyline(_polygon([(5.5, 5), (6.6, 3), (9.4, 3), (10.5, 5)]))
        p.drawEllipse(QPointF(8, 9.2), 2.4, 2.4)
    elif name == "click_through":  # mouse pointer
        p.setBrush(color)
        p.drawPolygon(_polygon([(3.5, 2), (3.5, 12.5), (6.2, 10), (8.2, 14), (10, 13.2), (8, 9.3), (11.5, 9.3)]))
    elif name == "clear":  # trash can
        p.drawLine(QPointF(3, 4.5), QPointF(13, 4.5))
        path = QPainterPath(QPointF(6, 4.5))
        path.lineTo(6, 2.5)
        path.lineTo(10, 2.5)
        path.lineTo(10, 4.5)
        p.drawPath(path)
        body = QPainterPath(QPointF(4.5, 4.5))
        body.lineTo(5.3, 13.5)
        body.lineTo(10.7, 13.5)
        body.lineTo(11.5, 4.5)
        p.drawPath(body)
    elif name == "quit":  # power symbol
        p.drawArc(QRectF(2.5, 3, 11, 11), 120 * 16, 300 * 16)
        p.drawLine(QPointF(8, 1.8), QPointF(8, 8))
    else:
        raise ValueError(f"unknown icon {name!r}")


def make_icon(name: str, color: str = "#c9cddb") -> QIcon:
    pixmap = QPixmap(SIZE * 2, SIZE * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    try:
        _draw(name, painter, QColor(color))
    finally:
        painter.end()
    return QIcon(pixmap)
