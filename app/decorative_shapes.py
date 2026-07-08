"""
Decorative Shapes
-------------------
Small, stateless drawing helpers used by multiple screens so the "flower"
and "star" motifs stay visually consistent everywhere (dark cosmic screens
and the light bloom dashboard alike).
"""

import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath, QPen, QRadialGradient


def draw_flower(painter, cx, cy, size, hue, alpha=190, center_hue="#E8B84B"):
    """Draws a simple 6-petal flower centered at (cx, cy)."""
    petal_color = QColor(hue)
    petal_color.setAlpha(alpha)
    center_color = QColor(center_hue)
    center_color.setAlpha(min(255, alpha + 40))

    petals = 6
    petal_w = size * 0.55
    petal_h = size * 1.0

    painter.save()
    painter.translate(cx, cy)
    for i in range(petals):
        angle = (360 / petals) * i
        painter.save()
        painter.rotate(angle)
        painter.setBrush(petal_color)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(-petal_w / 2, -petal_h, petal_w, petal_h * 0.62)
        painter.drawEllipse(rect)
        painter.restore()

    painter.setBrush(center_color)
    painter.setPen(Qt.PenStyle.NoPen)
    r = size * 0.18
    painter.drawEllipse(QPointF(0, 0), r, r)
    painter.restore()


def draw_flower_with_stem(painter, base_x, base_y, height, flower_size, hue,
                           stem_color="#8FBF8A", sway=0.0, leaf=True):
    """Draws a curved stem rising from (base_x, base_y) with a flower on top.
    Useful for the bottom-corner flower clusters on light backgrounds."""
    tip_x = base_x + sway
    tip_y = base_y - height

    stem_pen = QPen(QColor(stem_color))
    stem_pen.setWidthF(2.4)
    stem_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(stem_pen)

    path = QPainterPath()
    path.moveTo(base_x, base_y)
    ctrl_x = base_x + sway * 0.6
    path.cubicTo(
        QPointF(ctrl_x, base_y - height * 0.4),
        QPointF(tip_x, base_y - height * 0.75),
        QPointF(tip_x, tip_y),
    )
    painter.drawPath(path)

    if leaf:
        leaf_color = QColor(stem_color)
        leaf_color.setAlpha(190)
        painter.setBrush(leaf_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.save()
        mid_x = base_x + sway * 0.3
        mid_y = base_y - height * 0.42
        painter.translate(mid_x, mid_y)
        painter.rotate(-35)
        painter.drawEllipse(QRectF(-2, -10, 14, 7))
        painter.restore()

    draw_flower(painter, tip_x, tip_y, flower_size, hue)


def draw_star_field(painter, rect_w, rect_h, count=18, seed=3, t=0.0,
                     color=QColor(255, 255, 255), offset_x=0.0, offset_y=0.0):
    """Scatters small twinkling dots across a rect_w x rect_h area."""
    import random
    rng = random.Random(seed)
    painter.setPen(Qt.PenStyle.NoPen)
    for i in range(count):
        x = rng.uniform(0.0, 1.0) * rect_w + offset_x
        y = rng.uniform(0.0, 1.0) * rect_h + offset_y
        phase = rng.uniform(0, math.tau)
        speed = rng.uniform(0.6, 1.6)
        twinkle = 0.5 + 0.5 * math.sin(t * speed + phase)
        r = rng.uniform(1.0, 2.2) * (0.8 + 0.4 * twinkle)
        c = QColor(color)
        c.setAlpha(int(70 + 130 * twinkle))
        painter.setBrush(c)
        painter.drawEllipse(QPointF(x, y), r, r)


def draw_constellation(painter, points, edges, t=0.0,
                        line_color=QColor(150, 160, 210, 90),
                        node_color=QColor(225, 228, 255, 230)):
    """points: list of QPointF. edges: list of (i, j) index pairs."""
    line_pen = QPen(line_color)
    line_pen.setWidthF(1.1)
    painter.setPen(line_pen)
    for a, b in edges:
        painter.drawLine(points[a], points[b])

    for i, p in enumerate(points):
        pulse = 0.5 + 0.5 * math.sin(t * 1.4 + i)
        glow_r = 10 + 4 * pulse
        glow = QRadialGradient(p, glow_r)
        gc1 = QColor(node_color)
        gc1.setAlpha(int(70 * pulse) + 20)
        gc2 = QColor(node_color)
        gc2.setAlpha(0)
        glow.setColorAt(0, gc1)
        glow.setColorAt(1, gc2)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(p, glow_r, glow_r)

        painter.setBrush(node_color)
        painter.drawEllipse(p, 3.0, 3.0)