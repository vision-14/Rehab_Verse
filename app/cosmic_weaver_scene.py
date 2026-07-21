"""
Cosmic Weaver Scene
----------------------
Multi-constellation starfield for Cosmic Weaver, matching the dark cosmic
theme used elsewhere in the app (splash/login screens). Draws several
named constellations as connected star patterns with labels, over a
scattered background star field.

Call set_lit_stars(n) to light up the first n stars across the whole
scene, in constellation order. Use this to show session progress - e.g.
light up one more star per completed rep/hold, the same way Bloom Forest
blooms a flower per rep.

Each constellation's star positions are simplified/stylized versions of
the real shapes, not astronomically precise - the goal is a recognizable,
decorative scene, not a star chart.

This file defines TWO constellation sets - PAGE_1_CONSTELLATIONS (Ursa
Major, Ursa Minor, Cassiopeia, Perseus, Lyra, Leo, Orion) and
PAGE_2_CONSTELLATIONS (Draco, Cetus, Andromeda, Aquila, Pegasus, Cygnus).
CosmicWeaverScene renders whichever set it's given. See
cosmic_weaver_pager.py for the widget that shows Page 1, then slides
to Page 2 automatically once Page 1's stars are all lit.
"""

import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QRadialGradient, QFont, QPen

from decorative_shapes import draw_star_field

# ---- Page 1: Ursa Major, Ursa Minor, Cassiopeia, Perseus, Lyra, Leo, Orion ----
# Each constellation: relative (0-1) star positions, the edges connecting
# them (indices into "points"), and where its label sits.
PAGE_1_CONSTELLATIONS = [
    {
        "name": "URSA MAJOR",
        "label_pos": (0.155, 0.44),
        "points": [
            (0.10, 0.35), (0.14, 0.28), (0.18, 0.29), (0.17, 0.38),
            (0.25, 0.25), (0.31, 0.20), (0.38, 0.15),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 0), (2, 4), (4, 5), (5, 6)],
    },
    {
        "name": "URSA MINOR",
        "label_pos": (0.51, 0.34),
        "points": [
            (0.42, 0.30), (0.45, 0.22), (0.49, 0.20), (0.50, 0.30),
            (0.56, 0.35), (0.60, 0.28), (0.55, 0.10),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (2, 6)],
    },
    {
        "name": "CASSIOPEIA",
        "label_pos": (0.83, 0.30),
        "points": [
            (0.72, 0.12), (0.78, 0.24), (0.83, 0.10), (0.88, 0.22), (0.93, 0.08),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4)],
    },
    {
        "name": "PERSEUS",
        "label_pos": (0.47, 0.48),
        "points": [
            (0.42, 0.42), (0.45, 0.35), (0.48, 0.30), (0.52, 0.34), (0.50, 0.42),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)],
    },
    {
        "name": "LYRA",
        "label_pos": (0.605, 0.52),
        "points": [
            (0.57, 0.42), (0.60, 0.36), (0.64, 0.38), (0.63, 0.45), (0.58, 0.48),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4)],
    },
    {
        "name": "LEO",
        "label_pos": (0.72, 0.78),
        "points": [
            (0.66, 0.46), (0.68, 0.55), (0.66, 0.63),
            (0.72, 0.68), (0.80, 0.72), (0.86, 0.86),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
    },
    {
        "name": "ORION",
        "label_pos": (0.345, 0.90),
        "points": [
            (0.30, 0.55), (0.40, 0.55), (0.33, 0.62), (0.35, 0.63),
            (0.37, 0.64), (0.31, 0.72), (0.40, 0.85),
        ],
        "edges": [(0, 2), (1, 4), (2, 3), (3, 4), (2, 5), (4, 6)],
    },
]

# Backward-compat alias - kept in case anything imports the old name.
CONSTELLATIONS = PAGE_1_CONSTELLATIONS

# ---- Page 2: Draco, Cetus, Andromeda, Aquila, Pegasus, Cygnus ----
PAGE_2_CONSTELLATIONS = [
    {
        "name": "DRACO",
        "label_pos": (0.16, 0.47),
        "points": [
            (0.10, 0.42), (0.14, 0.32), (0.20, 0.34),
            (0.24, 0.24), (0.30, 0.26), (0.34, 0.20),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
    },
    {
        "name": "CETUS",
        "label_pos": (0.435, 0.62),
        "points": [
            (0.42, 0.55), (0.45, 0.42), (0.48, 0.30),
            (0.52, 0.35), (0.50, 0.48), (0.46, 0.58),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)],
    },
    {
        "name": "ANDROMEDA",
        "label_pos": (0.755, 0.34),
        "points": [
            (0.68, 0.30), (0.74, 0.22), (0.78, 0.28), (0.84, 0.18), (0.90, 0.24),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4)],
    },
    {
        "name": "AQUILA",
        "label_pos": (0.155, 0.86),
        "points": [
            (0.15, 0.65), (0.20, 0.58), (0.26, 0.62),
            (0.22, 0.72), (0.18, 0.80), (0.28, 0.78),
        ],
        "edges": [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (3, 5)],
    },
    {
        "name": "PEGASUS",
        "label_pos": (0.40, 0.92),
        "points": [
            (0.42, 0.60), (0.50, 0.58), (0.52, 0.66),
            (0.44, 0.68), (0.48, 0.78), (0.44, 0.86),
        ],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5)],
    },
    {
        "name": "CYGNUS",
        "label_pos": (0.71, 0.83),
        "points": [
            (0.72, 0.55), (0.72, 0.65), (0.72, 0.75), (0.64, 0.65), (0.80, 0.65),
        ],
        "edges": [(0, 1), (1, 2), (3, 1), (1, 4)],
    },
]

# Computed once at import time - exposed as plain module-level constants
# so OTHER files (e.g. session_data.py, cosmic_weaver_pager.py) can
# clamp star counts against real capacity WITHOUT needing to create a
# live QWidget instance. Kept in sync automatically since they're
# derived from the constellation lists themselves.
PAGE_1_TOTAL = sum(len(c["points"]) for c in PAGE_1_CONSTELLATIONS)
PAGE_2_TOTAL = sum(len(c["points"]) for c in PAGE_2_CONSTELLATIONS)
TOTAL_STAR_COUNT = PAGE_1_TOTAL  # backward-compat alias (Page 1's count, as before)


class CosmicWeaverScene(QWidget):
    def __init__(self, constellations=None, parent=None):
        super().__init__(parent)
        self._constellations = constellations if constellations is not None else PAGE_1_CONSTELLATIONS
        self._t = 0.0
        self._lit_count = 0
        self._total_stars = sum(len(c["points"]) for c in self._constellations)

        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)

    def showEvent(self, event):
        self._clock.start(45)
        super().showEvent(event)

    def hideEvent(self, event):
        self._clock.stop()
        super().hideEvent(event)

    def _tick(self):
        self._t += 0.045
        self.update()

    # ------------------------------------------------------------------
    def set_lit_stars(self, count):
        """Lights up the first `count` stars in THIS scene's constellation
        set, in order. Clamped to this scene's own total (call
        total_star_count() to know that number)."""
        self._lit_count = max(0, min(count, self._total_stars))
        self.update()

    def total_star_count(self):
        return self._total_stars

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_background(painter, w, h)
        draw_star_field(painter, w, h, count=90, seed=21, t=self._t,
                         color=QColor(200, 210, 255))

        star_index = 0
        for const in self._constellations:
            pts = [QPointF(x * w, y * h) for x, y in const["points"]]

            line_pen = QPen(QColor(150, 160, 210, 90))
            line_pen.setWidthF(1.0)
            painter.setPen(line_pen)
            for a, b in const["edges"]:
                painter.drawLine(pts[a], pts[b])

            for p in pts:
                is_lit = star_index < self._lit_count
                self._draw_star(painter, p, is_lit)
                star_index += 1

            label_font = QFont("Segoe UI", 8)
            label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
            painter.setFont(label_font)
            painter.setPen(QColor(140, 150, 200, 160))
            lx, ly = const["label_pos"]
            painter.drawText(QPointF(lx * w, ly * h), const["name"])

    def _draw_background(self, painter, w, h):
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor("#150A2E"))
        gradient.setColorAt(0.5, QColor("#1C1040"))
        gradient.setColorAt(1.0, QColor("#0F0824"))
        painter.fillRect(0, 0, w, h, gradient)

    def _draw_star(self, painter, point, is_lit):
        if is_lit:
            pulse = 0.6 + 0.4 * math.sin(self._t * 1.6)
            glow_r = 12 + 4 * pulse
            glow = QRadialGradient(point, glow_r)
            c1 = QColor("#FFD97A")
            c1.setAlpha(int(160 * pulse))
            c2 = QColor("#FFD97A")
            c2.setAlpha(0)
            glow.setColorAt(0, c1)
            glow.setColorAt(1, c2)
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(point, glow_r, glow_r)

            painter.setBrush(QColor("#FFF3D6"))
            painter.drawEllipse(point, 4.2, 4.2)
        else:
            painter.setBrush(QColor(190, 200, 255, 150))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(point, 3.0, 3.0)


# ----------------------------------------------------------------------
# Standalone preview: `python cosmic_weaver_scene.py` - includes a
# slider so you can try set_lit_stars(n) interactively. Shows Page 1
# only - see cosmic_weaver_pager.py for the two-page slide version.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget as QW, QVBoxLayout, QSlider, QLabel

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setFixedSize(900, 600)
    central = QW()
    layout = QVBoxLayout(central)
    layout.setContentsMargins(0, 0, 0, 0)

    scene = CosmicWeaverScene()
    layout.addWidget(scene, 1)

    controls = QW()
    controls.setStyleSheet("background: #150A2E;")
    controls_layout = QVBoxLayout(controls)
    label = QLabel(f"Lit stars: 0 / {scene.total_star_count()}")
    label.setStyleSheet("color: white;")
    controls_layout.addWidget(label)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(scene.total_star_count())
    slider.valueChanged.connect(lambda v: (scene.set_lit_stars(v), label.setText(f"Lit stars: {v} / {scene.total_star_count()}")))
    controls_layout.addWidget(slider)

    layout.addWidget(controls)
    window.setCentralWidget(central)
    window.show()
    sys.exit(app.exec())