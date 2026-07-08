"""
Cosmic Background
------------------
Shared animated background (stars, drifting particles, the "Star Weaver"
constellation, and the "Bloom Forest" flower cluster) used by every screen
in the app, so the splash screen and the login screen (and any screen you
add later) all share the exact same look and motion.

Subclass CosmicPage, and override draw_foreground(painter, w, h) to draw
your own content on top of the animated background. The animation timer
starts automatically when the page becomes visible and stops when it's
hidden (e.g. when a QStackedWidget switches away from it), so you don't
waste CPU animating a page nobody can see.
"""

import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QPen, QBrush
)


class CosmicPage(QWidget):
    """A QWidget page that paints the cosmic/bloom animated background."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._t = 0.0
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._drag_pos = None  # used to let the user drag the frameless window

        # Use a private RNG (not the global `random` module) so multiple
        # pages can each build their own star field from the same seed
        # without stepping on each other's state.
        rng = random.Random(7)

        self._stars = [
            {
                "x": rng.uniform(0.0, 1.0),
                "y": rng.uniform(0.0, 1.0),
                "r": rng.uniform(1.0, 2.6),
                "phase": rng.uniform(0, math.tau),
                "speed": rng.uniform(0.6, 1.6),
                "dx": rng.uniform(-0.012, 0.012),
                "dy": rng.uniform(-0.006, 0.006),
            }
            for _ in range(110)
        ]

        self._particles = [
            {
                "x": rng.uniform(0.0, 1.0),
                "y": rng.uniform(0.0, 1.0),
                "r": rng.uniform(2.5, 5.0),
                "phase": rng.uniform(0, math.tau),
                "dx": rng.uniform(-0.018, 0.018),
                "dy": rng.uniform(-0.02, -0.004),
                "tint": rng.choice(["#CDEFE8", "#D9CCF2", "#F0CBE6"]),
            }
            for _ in range(26)
        ]

        self._const_points = [
            (0.80, 0.16), (0.90, 0.22), (0.86, 0.33),
            (0.77, 0.40), (0.83, 0.50), (0.93, 0.46),
        ]
        self._const_edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]

        self._flowers = [
            {"x": 0.10, "y": 0.34, "size": 34, "hue": "#B9679A", "phase": 0.0},
            {"x": 0.16, "y": 0.46, "size": 50, "hue": "#C77BAE", "phase": 1.1},
            {"x": 0.09, "y": 0.60, "size": 40, "hue": "#B9679A", "phase": 2.2},
            {"x": 0.19, "y": 0.66, "size": 30, "hue": "#A85C93", "phase": 3.3},
        ]

    # ------------------------------------------------------------------
    # Lifecycle: only animate while actually visible
    # ------------------------------------------------------------------
    def showEvent(self, event):
        self._clock.start(33)  # ~30 fps
        super().showEvent(event)

    def hideEvent(self, event):
        self._clock.stop()
        super().hideEvent(event)

    def _tick(self):
        self._t += 0.033
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        self._draw_background(painter, w, h)
        self._draw_center_glow(painter, w, h)
        self._draw_stars(painter, w, h)
        self._draw_particles(painter, w, h)
        self._draw_constellation(painter, w, h)
        self._draw_flowers(painter, w, h)
        self.draw_foreground(painter, w, h)

    def draw_foreground(self, painter, w, h):
        """Override in subclasses to draw content on top of the background."""
        pass

    # ------------------------------------------------------------------
    # Since the top-level window is frameless, clicking and dragging any
    # empty part of the animated background moves the window. Clicks that
    # land on child widgets (buttons, inputs, etc.) are consumed by those
    # widgets first, so this never interferes with the login form.
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    def _draw_background(self, painter, w, h):
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor("#120A22"))
        gradient.setColorAt(0.5, QColor("#180F2C"))
        gradient.setColorAt(1.0, QColor("#0D0818"))
        painter.fillRect(0, 0, w, h, gradient)

    def _draw_center_glow(self, painter, w, h):
        glow = QRadialGradient(QPointF(w / 2, h * 0.42), w * 0.5)
        c1 = QColor("#3B2560")
        c1.setAlpha(110)
        c2 = QColor("#3B2560")
        c2.setAlpha(0)
        glow.setColorAt(0.0, c1)
        glow.setColorAt(1.0, c2)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, h)

    def _draw_stars(self, painter, w, h):
        painter.setPen(Qt.PenStyle.NoPen)
        for s in self._stars:
            x = (s["x"] + s["dx"] * self._t) % 1.0
            y = (s["y"] + s["dy"] * self._t) % 1.0
            twinkle = 0.5 + 0.5 * math.sin(self._t * s["speed"] + s["phase"])
            alpha = int(60 + 150 * twinkle)
            color = QColor(230, 225, 250, alpha)
            painter.setBrush(color)
            r = s["r"] * (0.8 + 0.4 * twinkle)
            painter.drawEllipse(QPointF(x * w, y * h), r, r)

    def _draw_particles(self, painter, w, h):
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            x = (p["x"] + p["dx"] * self._t) % 1.0
            y = (p["y"] + p["dy"] * self._t) % 1.0
            pulse = 0.5 + 0.5 * math.sin(self._t * 0.8 + p["phase"])
            cx, cy = x * w, y * h
            r = p["r"] * (0.85 + 0.3 * pulse)

            glow = QRadialGradient(QPointF(cx, cy), r * 3.2)
            c1 = QColor(p["tint"])
            c1.setAlpha(int(70 + 50 * pulse))
            c2 = QColor(p["tint"])
            c2.setAlpha(0)
            glow.setColorAt(0.0, c1)
            glow.setColorAt(1.0, c2)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(cx, cy), r * 3.2, r * 3.2)

            core = QColor(p["tint"])
            core.setAlpha(int(140 + 60 * pulse))
            painter.setBrush(core)
            painter.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_constellation(self, painter, w, h):
        pts = [QPointF(x * w, y * h) for x, y in self._const_points]

        line_pen = QPen(QColor(150, 160, 210, 90))
        line_pen.setWidthF(1.1)
        painter.setPen(line_pen)
        for a, b in self._const_edges:
            painter.drawLine(pts[a], pts[b])

        for i, p in enumerate(pts):
            pulse = 0.5 + 0.5 * math.sin(self._t * 1.4 + i)
            glow_r = 12 + 4 * pulse
            glow = QRadialGradient(p, glow_r)
            gc1 = QColor(190, 200, 255, int(70 * pulse) + 20)
            gc2 = QColor(190, 200, 255, 0)
            glow.setColorAt(0, gc1)
            glow.setColorAt(1, gc2)
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(p, glow_r, glow_r)

            painter.setBrush(QColor(225, 228, 255, 230))
            painter.drawEllipse(p, 3.4, 3.4)

    def _draw_flowers(self, painter, w, h):
        for f in self._flowers:
            sway = math.sin(self._t * 0.6 + f["phase"]) * 3
            cx = f["x"] * w + sway
            cy = f["y"] * h
            self._draw_single_flower(painter, cx, cy, f["size"], f["hue"])

    def _draw_single_flower(self, painter, cx, cy, size, hue):
        petal_color = QColor(hue)
        petal_color.setAlpha(150)
        center_color = QColor("#E8B84B")
        center_color.setAlpha(190)

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