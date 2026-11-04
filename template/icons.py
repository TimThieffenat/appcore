"""Icônes de l'app, dessinées en code (grille de 24 × 24, traits arrondis).

Le dessin et les icônes communes (réglages, lecture, stats, trophée, étoile…)
sont dans appcore/icons.py ; celles de l'app y sont enregistrées ici.
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
