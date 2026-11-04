"""Icônes dessinées en code (aucun fichier image), partagées par les apps.

Chaque icône est tracée sur une grille de 24 × 24, en traits arrondis, dans
la couleur demandée. `nav_icon` fait les icônes du rail (deux états) ;
`paint` dessine une icône dans un rectangle (cartes, trophées, bilan).

Le socle a les icônes de tous les jours (réglages, lecture, stats, trophée,
étoile, coche…). Chaque app ajoute les siennes dans son icons.py :

    from appcore.icons import *          # noqa: F403
    from appcore.icons import register

    def _neck(p, color): ...
    register("neck", _neck)

Une icône de l'app peut remplacer celle du socle du même nom.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

SIZE = 24
RATIO = 3.0  # dessinée en haute définition pour rester nette sur téléphone


def _note_head(p: QPainter, color: QColor, x: float, y: float, r: float = 2.6) -> None:
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(x, y), r, r * 0.8)
    p.restore()


def _play(p: QPainter, color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(8, 5)
    path.lineTo(19, 12)
    path.lineTo(8, 19)
    path.closeSubpath()
    p.drawPath(path)


def _stats(p: QPainter, color: QColor) -> None:
    p.drawLine(QPointF(3.5, 20.5), QPointF(20.5, 20.5))
    for x, top in ((6.5, 13), (12, 7), (17.5, 10)):
        p.drawRoundedRect(QRectF(x - 2, top, 4, 20.5 - top - 2.5), 1, 1)


def _trophy(p: QPainter, color: QColor) -> None:
    cup = QPainterPath()
    cup.moveTo(7, 4)
    cup.lineTo(17, 4)
    cup.lineTo(17, 9)
    cup.quadTo(17, 14.5, 12, 14.5)
    cup.quadTo(7, 14.5, 7, 9)
    cup.closeSubpath()
    p.drawPath(cup)
    p.drawArc(QRectF(3, 5.5, 5, 5), 90 * 16, 180 * 16)
    p.drawArc(QRectF(16, 5.5, 5, 5), -90 * 16, 180 * 16)
    p.drawLine(QPointF(12, 14.5), QPointF(12, 18))
    p.drawLine(QPointF(8, 20), QPointF(16, 20))
    p.drawLine(QPointF(9, 18), QPointF(15, 18))


def _settings(p: QPainter, color: QColor) -> None:
    for y, knob in ((6.5, 8.0), (12.0, 15.5), (17.5, 10.5)):
        p.drawLine(QPointF(3, y), QPointF(21, y))
        p.save()
        p.setBrush(color)
        p.drawEllipse(QPointF(knob, y), 2.2, 2.2)
        p.restore()


def _calendar(p: QPainter, color: QColor) -> None:
    p.drawRoundedRect(QRectF(3.5, 5, 17, 15.5), 3, 3)
    p.drawLine(QPointF(3.5, 9.5), QPointF(20.5, 9.5))
    p.drawLine(QPointF(8, 3), QPointF(8, 6.5))
    p.drawLine(QPointF(16, 3), QPointF(16, 6.5))
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(12, 15), 2.2, 2.2)
    p.restore()


def _flame(p: QPainter, color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(12, 2.5)
    path.cubicTo(13, 7, 19, 9, 18.5, 15)
    path.cubicTo(18.2, 19, 15, 21.5, 12, 21.5)
    path.cubicTo(9, 21.5, 5.8, 19, 5.5, 15)
    path.cubicTo(5.3, 11.5, 8, 10, 8.5, 7.5)
    path.cubicTo(10, 9.5, 10, 11, 10, 12.5)
    path.cubicTo(11.5, 10, 12.5, 6.5, 12, 2.5)
    p.save()
    p.setBrush(color)
    p.drawPath(path)
    p.restore()


def _snow(p: QPainter, color: QColor) -> None:
    for angle in (0, 60, 120):
        p.save()
        p.translate(12, 12)
        p.rotate(angle)
        p.drawLine(QPointF(0, -9), QPointF(0, 9))
        for s in (-1, 1):
            p.drawLine(QPointF(0, 6 * s), QPointF(-2.5, 8.5 * s))
            p.drawLine(QPointF(0, 6 * s), QPointF(2.5, 8.5 * s))
        p.restore()


def star_path(cx: float, cy: float, outer: float, inner: float | None = None) -> QPainterPath:
    import math
    inner = outer * 0.47 if inner is None else inner
    path = QPainterPath()
    for k in range(10):
        r = outer if k % 2 == 0 else inner
        a = -math.pi / 2 + k * math.pi / 5
        point = QPointF(cx + r * math.cos(a), cy + r * math.sin(a))
        if k == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


def _star(p: QPainter, color: QColor) -> None:
    p.save()
    p.setBrush(color)
    p.drawPath(star_path(12, 12.6, 9.5))
    p.restore()


def _target(p: QPainter, color: QColor) -> None:
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawEllipse(QPointF(12, 12), 5, 5)
    p.save()
    p.setBrush(color)
    p.drawEllipse(QPointF(12, 12), 1.6, 1.6)
    p.restore()


def _compass(p: QPainter, color: QColor) -> None:
    p.drawEllipse(QPointF(12, 12), 9, 9)
    needle = QPainterPath()
    needle.moveTo(15.5, 8.5)
    needle.lineTo(13.2, 13.2)
    needle.lineTo(8.5, 15.5)
    needle.lineTo(10.8, 10.8)
    needle.closeSubpath()
    p.save()
    p.setBrush(color)
    p.drawPath(needle)
    p.restore()


def _level(p: QPainter, color: QColor) -> None:
    # chevrons qui montent
    for y in (16, 10.5, 5):
        p.drawLine(QPointF(6, y + 3.5), QPointF(12, y))
        p.drawLine(QPointF(12, y), QPointF(18, y + 3.5))


def _check(p: QPainter, color: QColor) -> None:
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawLine(QPointF(7.5, 12.5), QPointF(10.8, 15.8))
    p.drawLine(QPointF(10.8, 15.8), QPointF(16.8, 8.8))


def _lock(p: QPainter, color: QColor) -> None:
    p.drawRoundedRect(QRectF(5.5, 10.5, 13, 10), 2.5, 2.5)
    p.drawArc(QRectF(8, 3.5, 8, 11), 0, 180 * 16)
    p.drawLine(QPointF(8, 9), QPointF(8, 10.5))
    p.drawLine(QPointF(16, 9), QPointF(16, 10.5))


def _speaker(p: QPainter, color: QColor) -> None:
    body = QPainterPath()
    body.moveTo(3.5, 9.5)
    body.lineTo(7.5, 9.5)
    body.lineTo(12.5, 5)
    body.lineTo(12.5, 19)
    body.lineTo(7.5, 14.5)
    body.lineTo(3.5, 14.5)
    body.closeSubpath()
    p.save()
    p.setBrush(color)
    p.drawPath(body)
    p.restore()
    p.drawArc(QRectF(10, 8, 7, 8), -55 * 16, 110 * 16)
    p.drawArc(QRectF(9.5, 4.5, 11.5, 15), -55 * 16, 110 * 16)


def _close(p: QPainter, color: QColor) -> None:
    p.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
    p.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))


def _create(p: QPainter, color: QColor) -> None:
    p.drawRoundedRect(QRectF(3.5, 3.5, 17, 17), 4.5, 4.5)
    p.drawLine(QPointF(12, 8), QPointF(12, 16))
    p.drawLine(QPointF(8, 12), QPointF(16, 12))


def _unknown(p: QPainter, color: QColor) -> None:
    """Icône d'un nom inconnu : un rond (rien ne plante s'il en manque une)."""
    p.drawEllipse(QPointF(12, 12), 7, 7)


DRAWERS = {
    "settings": _settings, "play": _play, "stats": _stats, "trophies": _trophy,
    "trophy": _trophy, "create": _create, "calendar": _calendar, "daily": _calendar,
    "flame": _flame, "snow": _snow, "star": _star, "target": _target, "compass": _compass,
    "level": _level, "check": _check, "lock": _lock, "speaker": _speaker, "close": _close,
}


def register(name: str, drawer) -> None:
    """Ajoute (ou remplace) une icône : drawer(p, couleur) dessine sur la grille 24 × 24,
    avec le crayon déjà réglé (couleur, épaisseur 1,7, bouts ronds) et sans remplissage."""
    DRAWERS[name] = drawer


def note_head(p: QPainter, color: QColor, x: float, y: float, r: float = 2.6) -> None:
    """Tête de note pleine (pour les icônes de musique des apps)."""
    _note_head(p, color, x, y, r)


def paint(p: QPainter, name: str, rect: QRectF, color: str | QColor, width: float = 1.7) -> None:
    """Dessine l'icône `name` dans `rect` (carré conseillé)."""
    qcolor = QColor(color)
    side = min(rect.width(), rect.height())
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(rect.center().x() - side / 2, rect.center().y() - side / 2)
    p.scale(side / SIZE, side / SIZE)
    p.setPen(QPen(qcolor, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    DRAWERS.get(name, _unknown)(p, qcolor)
    p.restore()


def _pixmap(name: str, color: str) -> QPixmap:
    pm = QPixmap(int(SIZE * RATIO), int(SIZE * RATIO))
    pm.setDevicePixelRatio(RATIO)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    paint(p, name, QRectF(0, 0, SIZE, SIZE), color)
    p.end()
    return pm


def nav_icon(name: str, normal: str, active: str) -> QIcon:
    """Icône à deux états : grise (bouton relâché) et accentuée (page active)."""
    icon = QIcon()
    icon.addPixmap(_pixmap(name, normal), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_pixmap(name, active), QIcon.Mode.Normal, QIcon.State.On)
    return icon
