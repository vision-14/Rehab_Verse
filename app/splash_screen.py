"""
Rehab Verse - Splash Screen (Cosmic / Bloom theme)
----------------------------------------------------
This is now a PAGE, not its own window. It's meant to be dropped into a
QStackedWidget (see main.py) alongside LoginPage so the whole app lives in
one persistent frameless window and screens crossfade in place instead of
one window closing and another opening.

Call splash.run(hold_ms) after showing it; it plays the intro animation for
`hold_ms` milliseconds and then emits `finished`, which main.py listens for
to trigger the crossfade into the login screen.

Run this file directly to preview just the splash screen on its own.
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QLinearGradient, QFont, QPen, QBrush, QPainterPath

from cosmic_background import CosmicPage


class SplashScreen(CosmicPage):
    """Cosmic bloom splash content: gradient title + shimmering loading bar."""

    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading_pos = 0.0

    def _tick(self):
        # extend the base tick to also advance the loading-bar sweep
        super()._tick()
        self._loading_pos = (self._loading_pos + 0.012) % 1.4

    # ------------------------------------------------------------------
    def draw_foreground(self, painter, w, h):
        self._draw_title_block(painter, w, h)
        self._draw_loading_bar(painter, w, h)

    def _draw_title_block(self, painter, w, h):
        center_x = w / 2
        top_y = h * 0.36

        kicker_font = QFont("Segoe UI", 9)
        kicker_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.2)
        painter.setFont(kicker_font)
        kicker_text = "REHABILITATION  \u00b7  REIMAGINED"
        metrics = painter.fontMetrics()
        kicker_width = metrics.horizontalAdvance(kicker_text)
        painter.setPen(QColor(150, 160, 200, 170))
        painter.drawText(QPointF(center_x - kicker_width / 2, top_y), kicker_text)

        line_pen = QPen(QColor(140, 150, 200, 110))
        line_pen.setWidthF(1.0)
        painter.setPen(line_pen)
        gap = 18
        painter.drawLine(
            QPointF(center_x - kicker_width / 2 - 46, top_y - 4),
            QPointF(center_x - kicker_width / 2 - gap, top_y - 4),
        )
        painter.drawLine(
            QPointF(center_x + kicker_width / 2 + gap, top_y - 4),
            QPointF(center_x + kicker_width / 2 + 46, top_y - 4),
        )

        title_font = QFont("Segoe UI", 46)
        title_font.setWeight(QFont.Weight.Light)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 9)
        title_text = "REHABVERSE"

        baseline_y = top_y + 78
        path = QPainterPath()
        path.addText(0, baseline_y, title_font, title_text)

        bbox = path.boundingRect()
        x_offset = center_x - bbox.center().x()
        path.translate(x_offset, 0)
        bbox = path.boundingRect()

        title_gradient = QLinearGradient(bbox.left(), 0, bbox.right(), 0)
        title_gradient.setColorAt(0.0, QColor("#8FE3E0"))
        title_gradient.setColorAt(0.5, QColor("#B8A3EF"))
        title_gradient.setColorAt(1.0, QColor("#E3A6E8"))

        painter.setPen(Qt.PenStyle.NoPen)
        glow_color = QColor("#9C8AD9")
        glow_color.setAlpha(50)
        painter.setBrush(glow_color)
        painter.drawPath(path.translated(0, 2))

        painter.setBrush(QBrush(title_gradient))
        painter.drawPath(path)

        sub_font = QFont("Segoe UI", 11)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        painter.setFont(sub_font)
        sub_text = "BLOOM  \u00b7  REACH  \u00b7  HEAL"
        sub_metrics = painter.fontMetrics()
        sub_width = sub_metrics.horizontalAdvance(sub_text)
        painter.setPen(QColor(175, 180, 215, 190))
        painter.drawText(QPointF(center_x - sub_width / 2, baseline_y + 42), sub_text)

    def _draw_loading_bar(self, painter, w, h):
        bar_width = 190
        bar_x = w / 2 - bar_width / 2
        bar_y = h * 0.82

        track_pen = QPen(QColor(255, 255, 255, 35))
        track_pen.setWidthF(1.4)
        painter.setPen(track_pen)
        painter.drawLine(QPointF(bar_x, bar_y), QPointF(bar_x + bar_width, bar_y))

        shimmer_len = 46
        cycle = self._loading_pos / 1.4
        pos = 1.0 - abs(1.0 - 2.0 * cycle)
        travel = bar_width - shimmer_len
        sx = bar_x + pos * travel

        shimmer_gradient = QLinearGradient(sx, bar_y, sx + shimmer_len, bar_y)
        c_edge = QColor(180, 190, 255, 0)
        c_mid = QColor(220, 210, 255, 220)
        shimmer_gradient.setColorAt(0.0, c_edge)
        shimmer_gradient.setColorAt(0.5, c_mid)
        shimmer_gradient.setColorAt(1.0, c_edge)
        shimmer_pen = QPen(QBrush(shimmer_gradient), 2.0)
        painter.setPen(shimmer_pen)
        painter.drawLine(QPointF(sx, bar_y), QPointF(sx + shimmer_len, bar_y))

        label_font = QFont("Segoe UI", 9)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        painter.setFont(label_font)
        dot_count = int(self._t * 1.6) % 4
        label = "LOADING" + "." * dot_count
        painter.setPen(QColor(150, 155, 195, 160))
        label_metrics = painter.fontMetrics()
        label_width = label_metrics.horizontalAdvance("LOADING...")
        painter.drawText(QPointF(w / 2 - label_width / 2, bar_y + 26), label)

    # ------------------------------------------------------------------
    def run(self, hold_ms=2600):
        """Hold on the splash animation for hold_ms, then emit `finished`."""
        QTimer.singleShot(hold_ms, self.finished.emit)


# ----------------------------------------------------------------------
# Standalone preview: `python splash_screen.py`
# ----------------------------------------------------------------------
class _PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(900, 560)
        self.splash = SplashScreen(self)
        self.splash.setGeometry(0, 0, 900, 560)
        self.splash.finished.connect(QApplication.instance().quit)

    def showEvent(self, event):
        super().showEvent(event)
        self.splash.run(2600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = _PreviewWindow()
    win.show()
    sys.exit(app.exec())