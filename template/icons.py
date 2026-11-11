"""The app's icons, drawn in code (24 × 24 grid, rounded strokes).

The drawing and the common icons (settings, play, stats, trophy, star…)
are in appcore/icons.py; the app's are registered there from here.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath

from appcore.icons import *  # noqa: F403 — nav_icon, paint…
from appcore.icons import register


def _home(p: QPainter, color: QColor) -> None:
    roof = QPainterPath()
    roof.moveTo(3.5, 11.5)
    roof.lineTo(12, 4)
    roof.lineTo(20.5, 11.5)
    p.drawPath(roof)
    p.drawRoundedRect(QRectF(6, 10.5, 12, 10), 1.5, 1.5)
    p.drawLine(QPointF(12, 20.5), QPointF(12, 15.5))


register("home", _home)
