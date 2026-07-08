"""
Progress View
---------------
The "Progress" tab: overall stats (current streak, best streak, total
sessions), a bigger weekly activity tracker, and a small breakdown per
game. All numbers here are placeholders until MongoDB is wired in - each
setter is named for exactly what it should be fed.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from weekly_activity import WeeklyActivityCard
from session_data import get_weekly_session_days, get_current_streak


def _stat_card(value_text, label_text, accent="#7C5CE0"):
    card = QFrame()
    card.setFixedHeight(88)
    card.setStyleSheet("""
        QFrame {
            background-color: rgba(255, 255, 255, 225);
            border-radius: 16px;
        }
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(2)

    value = QLabel(value_text)
    value_font = QFont("Segoe UI", 22)
    value_font.setWeight(QFont.Weight.Bold)
    value.setFont(value_font)
    value.setStyleSheet(f"color: {accent}; background: transparent;")
    layout.addWidget(value)

    label = QLabel(label_text)
    label.setStyleSheet("color: #8A7CB0; background: transparent; font-size: 11px;")
    layout.addWidget(label)
    layout.addStretch()

    return card, value


class ProgressView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 20)
        layout.setSpacing(22)

        heading = QLabel("Your Progress")
        heading_font = QFont("Segoe UI", 22)
        heading_font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #2E2350; background: transparent;")
        layout.addWidget(heading)

        # ---- stat cards ----
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        current_card, self.current_streak_value = _stat_card(
            str(get_current_streak()), "Current Streak (days)", "#7C5CE0"
        )
        best_card, self.best_streak_value = _stat_card("12", "Best Streak (days)", "#C77BAE")
        total_card, self.total_sessions_value = _stat_card("38", "Total Sessions", "#8FE3E0")

        stats_row.addWidget(current_card)
        stats_row.addWidget(best_card)
        stats_row.addWidget(total_card)
        layout.addLayout(stats_row)

        # ---- weekly activity, bigger ----
        self.weekly_activity = WeeklyActivityCard(dot_size=16)
        layout.addWidget(self.weekly_activity)
        # TODO: self.weekly_activity.set_sessions(mongo_get_last_7_days_sessions(user_id))
        self.weekly_activity.set_sessions(get_weekly_session_days())

        # ---- per-game breakdown ----
        breakdown_row = QHBoxLayout()
        breakdown_row.setSpacing(20)

        bloom_card, self.bloom_sessions_value = _stat_card("21", "Bloom Forest sessions", "#C77BAE")
        cosmic_card, self.cosmic_sessions_value = _stat_card("17", "Cosmic Weaver sessions", "#8FE3E0")
        breakdown_row.addWidget(bloom_card)
        breakdown_row.addWidget(cosmic_card)
        layout.addLayout(breakdown_row)

        layout.addStretch()

    # ------------------------------------------------------------------
    def set_current_streak(self, days):
        self.current_streak_value.setText(str(days))

    def set_best_streak(self, days):
        self.best_streak_value.setText(str(days))

    def set_total_sessions(self, count):
        self.total_sessions_value.setText(str(count))

    def set_game_sessions(self, bloom_forest_count, cosmic_weaver_count):
        self.bloom_sessions_value.setText(str(bloom_forest_count))
        self.cosmic_sessions_value.setText(str(cosmic_weaver_count))