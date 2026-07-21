"""
Progress Chart
----------------
A small custom-drawn LINE chart (no charting library dependency) with a
real labeled y-axis (value + unit at each gridline) and x-axis (session
number 1..N, not calendar dates - matches what was actually asked for).
One or more series plotted as straight-line-segments-between-points (a
real line chart, not an interpolated/fabricated curve) with small
circular markers at each actual session's data point.

Call load(history, series, y_max, y_suffix) with:
  history:  session_data.get_session_history()'s output
  series:   [{"key": "flexion_rom", "label": "Flexion", "color": "#7C5CE0"}, ...]
            - one dict per line to draw, "key" matching a field in history
  y_max:    the top of the y-axis. Pass a fixed number for metrics with a
            natural ceiling (e.g. 100 for a percentage, 90 for degrees).
            Pass None for unbounded metrics (raw counts like stars
            deposited/dropped, wrong-hand attempts, score) - the chart
            will compute a ceiling from the actual data instead, with a
            bit of headroom, so it never clips a real value at the top.
  y_suffix: unit shown next to each y-axis value, e.g. "%" or "\u00b0"
"""

import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath


class ProgressChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []
        self._series = []
        self._y_max = 100
        self._y_suffix = ""
        self.setMinimumHeight(160)

    def load(self, history, series, y_max=100, y_suffix=""):
        self._history = history or []
        self._series = series or []
        self._y_suffix = y_suffix

        # y_max=None means "figure it out from the real data" - used for
        # unbounded count metrics that have no natural percentage/degree
        # ceiling, so a hardcoded guess would either clip real values or
        # leave the chart mostly empty.
        self._y_max = y_max if y_max is not None else self._auto_y_max()
        self.update()

    def _auto_y_max(self):
        """Computes a sensible y-axis ceiling from the actual loaded
        history/series instead of a hardcoded guess - takes the highest
        value across all series and adds 20% headroom so the peak point
        isn't drawn flush against the top edge. Falls back to a small
        default if there's no data yet (e.g. brand new user)."""
        values = []
        for entry in self._history:
            for s in self._series:
                val = entry.get(s["key"])
                if val is not None:
                    values.append(val)

        if not values:
            return 10  # no data yet - a small default so the axis still reads sensibly

        peak = max(values)
        if peak <= 0:
            return 10

        return max(math.ceil(peak * 1.2), 1)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._history or not self._series:
            painter.setPen(QColor("#8A7CB0"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                              "No sessions yet \u2014 play a round to see your progress here.")
            return

        left_pad = 40   # room for y-axis value labels
        right_pad = 10
        top_pad = 14
        bottom_pad = 24
        chart_h = h - top_pad - bottom_pad
        chart_w = w - left_pad - right_pad
        n = len(self._history)

        label_font = QFont("Segoe UI", 8)
        painter.setFont(label_font)

        # ---- y-axis: gridlines WITH value labels (this was missing before) ----
        for frac in (0.0, 0.5, 1.0):
            y = top_pad + chart_h * (1 - frac)

            grid_pen = QPen(QColor(235, 230, 248))
            grid_pen.setWidthF(1.0)
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(left_pad, y), QPointF(left_pad + chart_w, y))

            value = self._y_max * frac
            painter.setPen(QColor("#A79BC7"))
            label = f"{value:.0f}{self._y_suffix}"
            painter.drawText(
                QRectF(0, y - 8, left_pad - 8, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )

        # ---- axis lines ----
        axis_pen = QPen(QColor("#C9B7EC"))
        axis_pen.setWidthF(1.2)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(left_pad, top_pad), QPointF(left_pad, top_pad + chart_h))
        painter.drawLine(QPointF(left_pad, top_pad + chart_h), QPointF(left_pad + chart_w, top_pad + chart_h))

        def x_for(i):
            if n == 1:
                return left_pad + chart_w / 2
            return left_pad + chart_w * i / (n - 1)

        def y_for(value):
            ratio = max(0.0, min(1.0, value / self._y_max)) if value is not None else 0.0
            return top_pad + chart_h * (1 - ratio)

        # ---- the actual line(s) ----
        for s in self._series:
            points = []
            for i, entry in enumerate(self._history):
                val = entry.get(s["key"])
                if val is None:
                    continue
                points.append(QPointF(x_for(i), y_for(val)))

            if not points:
                continue

            color = QColor(s["color"])
            if len(points) >= 2:
                path = QPainterPath()
                path.moveTo(points[0])
                for pt in points[1:]:
                    path.lineTo(pt)
                line_pen = QPen(color)
                line_pen.setWidthF(2.2)
                line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(line_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for pt in points:
                painter.drawEllipse(pt, 3.4, 3.4)

        # ---- x-axis: session number 1..N under every point, clamped so
        # the first/last labels never get cut off past the widget edge
        # (that's what was rendering as "'/16" instead of a real date) ----
        painter.setPen(QColor("#A79BC7"))
        painter.setFont(label_font)
        label_w = 22
        for i in range(n):
            x = x_for(i)
            rect_x = max(0.0, min(w - label_w, x - label_w / 2))
            painter.drawText(
                QRectF(rect_x, top_pad + chart_h + 6, label_w, 16),
                Qt.AlignmentFlag.AlignCenter,
                str(i + 1)
            )