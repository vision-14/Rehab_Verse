"""
Bloom Background
------------------
The light lavender/pink theme used post-login: soft gradient wash, gentle
sparkle dots, layered mountain silhouettes, and a flower cluster growing
from the bottom-right corner. Mirrors the role cosmic_background.py plays
for the dark screens - subclass BloomPage and lay your own widgets/layout
on top of it.
"""

import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QRadialGradient

from decorative_shapes import draw_star_field, draw_flower_with_stem


class BloomPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)

        rng = random.Random(9)
        self._particles = [
            {
                "x": rng.uniform(0.0, 1.0),
                "y": rng.uniform(0.0, 0.75),
                "r": rng.uniform(2.0, 4.0),
                "phase": rng.uniform(0, math.tau),
                "dx": rng.uniform(-0.012, 0.012),
                "dy": rng.uniform(-0.012, -0.003),
                "tint": rng.choice(["#C9B7EC", "#E3B6D6", "#B8A3EF"]),
            }
            for _ in range(16)
        ]

    def showEvent(self, event):
        self._clock.start(40)  # gentle ~25fps, this theme is subtle
        super().showEvent(event)

    def hideEvent(self, event):
        self._clock.stop()
        super().hideEvent(event)

    def _tick(self):
        self._t += 0.04
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        self._draw_wash(painter, w, h)
        self._draw_sparkles(painter, w, h)
        self._draw_particles(painter, w, h)
        self._draw_mountains(painter, w, h)
        self._draw_flower_cluster(painter, w, h)
        self.draw_foreground(painter, w, h)

    def draw_foreground(self, painter, w, h):
        """Override to draw extra content above the background, if needed."""
        pass

    # ------------------------------------------------------------------
    def _draw_wash(self, painter, w, h):
        gradient = QLinearGradient(0, 0, w * 0.4, h)
        gradient.setColorAt(0.0, QColor("#DCD3F5"))
        gradient.setColorAt(0.45, QColor("#E7DEF6"))
        gradient.setColorAt(1.0, QColor("#F6EEF6"))
        painter.fillRect(0, 0, w, h, gradient)

    def _draw_sparkles(self, painter, w, h):
        draw_star_field(
            painter, w, h * 0.7, count=26, seed=11, t=self._t,
            color=QColor(150, 130, 200),
        )

    def _draw_particles(self, painter, w, h):
        """Slow-drifting soft glow particles - gives the screen a gentle
        sense of life without being distracting."""
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            x = (p["x"] + p["dx"] * self._t) % 1.0
            y = (p["y"] + p["dy"] * self._t) % 1.0
            pulse = 0.5 + 0.5 * math.sin(self._t * 0.7 + p["phase"])
            cx, cy = x * w, y * h
            r = p["r"] * (0.85 + 0.3 * pulse)

            glow = QRadialGradient(QPointF(cx, cy), r * 3.0)
            c1 = QColor(p["tint"])
            c1.setAlpha(int(50 + 40 * pulse))
            c2 = QColor(p["tint"])
            c2.setAlpha(0)
            glow.setColorAt(0.0, c1)
            glow.setColorAt(1.0, c2)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(cx, cy), r * 3.0, r * 3.0)

            core = QColor(p["tint"])
            core.setAlpha(int(120 + 60 * pulse))
            painter.setBrush(core)
            painter.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_mountains(self, painter, w, h):
        layers = [
            {"base": 0.86, "amp": 0.05, "color": "#C9B7EC", "alpha": 90, "phase": 0.0},
            {"base": 0.92, "amp": 0.045, "color": "#D6C3EE", "alpha": 120, "phase": 1.6},
            {"base": 0.97, "amp": 0.035, "color": "#E7D6ED", "alpha": 160, "phase": 3.0},
        ]
        for layer in layers:
            path = QPainterPath()
            path.moveTo(0, h)
            base_y = h * layer["base"]
            amp = h * layer["amp"]
            steps = 24
            path.lineTo(0, base_y)
            for i in range(steps + 1):
                x = w * i / steps
                y = base_y + amp * math.sin(i * 0.9 + layer["phase"] + self._t * 0.12)
                path.lineTo(x, y)
            path.lineTo(w, h)
            path.closeSubpath()

            color = QColor(layer["color"])
            color.setAlpha(layer["alpha"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPath(path)

    def _draw_flower_cluster(self, painter, w, h):
        sway = math.sin(self._t * 0.5) * 2
        base_y = h + 6
        flowers = [
            {"x": w - 34, "height": 92, "size": 30, "hue": "#B983C9"},
            {"x": w - 78, "height": 128, "size": 40, "hue": "#C79FE0"},
            {"x": w - 118, "height": 78, "size": 26, "hue": "#A96FBE"},
        ]
        for f in flowers:
            draw_flower_with_stem(
                painter, f["x"], base_y, f["height"], f["size"], f["hue"],
                stem_color="#9FB88C", sway=sway,
            )