"""
Weekly Activity Card
-----------------------
A small card: header + a decorative trend icon, a one-line summary, and a
row of 7 days (Mon-Sun) with a dot above each day that had a logged
session. Today's letter is highlighted so it's easy to spot at a glance.

Call set_sessions() with a fresh 7-item boolean list whenever you have real
data from MongoDB - see session_data.py for the expected shape.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from session_data import DAY_LETTERS, get_today_index

DOT_EMPTY_STYLE = "background-color: rgba(124, 92, 224, 35); border-radius: 6px;"
DOT_FILLED_STYLE = "background-color: #7C5CE0; border-radius: 6px;"
DOT_TODAY_RING = "border: 2px solid #B983C9;"


def _summary_for(sessions):
    active_days = sum(1 for v in sessions if v)
    if active_days >= 5:
        return "Amazing consistency this week!"
    if active_days >= 3:
        return "Great progress this week!"
    if active_days >= 1:
        return "Nice start \u2014 keep it up!"
    return "Let's get moving today!"


class WeeklyActivityCard(QFrame):
    def __init__(self, parent=None, dot_size=13):
        super().__init__(parent)
        self._dot_size = dot_size
        self._dots = []
        self._sessions = [False] * 7
        self._today_idx = get_today_index()
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 225);
                border-radius: 18px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("WEEKLY ACTIVITY")
        title_font = QFont("Segoe UI", 9)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        title.setFont(title_font)
        title.setStyleSheet("color: #8A7CB0; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()

        icon = QLabel("\U0001F4C8")
        icon.setFixedSize(28, 28)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("""
            background-color: #7C5CE0;
            border-radius: 14px;
            font-size: 13px;
        """)
        header_row.addWidget(icon)
        layout.addLayout(header_row)

        self.summary_label = QLabel()
        summary_font = QFont("Segoe UI", 12)
        summary_font.setWeight(QFont.Weight.DemiBold)
        self.summary_label.setFont(summary_font)
        self.summary_label.setStyleSheet("color: #3D2E63; background: transparent;")
        layout.addWidget(self.summary_label)
        layout.addSpacing(6)

        grid = QGridLayout()
        grid.setSpacing(10)
        for col, letter in enumerate(DAY_LETTERS):
            dot = QLabel()
            dot.setFixedSize(self._dot_size, self._dot_size)
            dot.setStyleSheet(DOT_EMPTY_STYLE)
            grid.addWidget(dot, 0, col, Qt.AlignmentFlag.AlignHCenter)
            self._dots.append(dot)

            day_label = QLabel(letter)
            day_font = QFont("Segoe UI", 9)
            if col == self._today_idx:
                day_font.setWeight(QFont.Weight.Bold)
                day_label.setStyleSheet("color: #7C5CE0; background: transparent;")
            else:
                day_label.setStyleSheet("color: #A79BC7; background: transparent;")
            day_label.setFont(day_font)
            grid.addWidget(day_label, 1, col, Qt.AlignmentFlag.AlignHCenter)

        layout.addLayout(grid)
        self._refresh()

    # ------------------------------------------------------------------
    def set_sessions(self, sessions):
        """sessions: list of 7 booleans, index 0 = Monday, 6 = Sunday."""
        if len(sessions) != 7:
            raise ValueError("set_sessions expects exactly 7 values (Mon-Sun)")
        self._sessions = list(sessions)
        self._refresh()

    def _refresh(self):
        self.summary_label.setText(_summary_for(self._sessions))
        for i, dot in enumerate(self._dots):
            style = DOT_FILLED_STYLE if self._sessions[i] else DOT_EMPTY_STYLE
            if i == self._today_idx:
                style += DOT_TODAY_RING
            dot.setStyleSheet(style)