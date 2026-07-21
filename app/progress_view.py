"""
Progress View
---------------
The "Progress" tab: overall stats (current streak, best streak, total
sessions), a bigger weekly activity tracker, and a per-game breakdown -
all real numbers for the logged-in user, pulled from MongoDB via
session_data.py.

Only the two per-game cards (Bloom Forest / Cosmic Weaver) are clickable
- Total Sessions is just a plain number. Clicking a game card opens that
game's graphical progress reports: line charts (not bar charts) built
from GAME_CHART_CONFIGS below, which is where you define what each game
actually tracks.

Call refresh_for_user(user_id) whenever this should show fresh data -
the dashboard does this at login and every time this tab is opened.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from weekly_activity import WeeklyActivityCard
from progress_chart import ProgressChart
from session_data import (
    get_weekly_session_days, get_current_streak, get_best_streak,
    get_total_sessions, get_game_session_counts, get_session_history,
    get_game_display_name,
)
from stat_card import make_stat_card
from night_sky_view import NightSkyView

# ----------------------------------------------------------------------
# Defines exactly what graphical reports each game shows when its card is
# clicked. Each game gets a LIST of chart panels.
#
# "y_max": a fixed number for metrics with a natural ceiling (percentages,
# degrees). Omit the key (or set it to None) for unbounded count metrics -
# ProgressChart will then compute a ceiling from the actual session data
# instead of clipping real values against a hardcoded guess.
GAME_CHART_CONFIGS = {
    "bloom_forest": [
        {
            "title": "Range of Motion",
            "y_max": 90,
            "y_suffix": "\u00b0",
            "series": [
                {"key": "flexion_rom", "label": "Flexion", "color": "#7C5CE0"},
                {"key": "extension_rom", "label": "Extension", "color": "#C77BAE"},
            ],
        },
        {
            "title": "Accuracy",
            "y_max": 100,
            "y_suffix": "%",
            "series": [
                {"key": "accuracy", "label": "Accuracy", "color": "#8FE3E0"},
            ],
        },
        {
            "title": "Max Hold Time",
            "y_max": 15,
            "y_suffix": "s",
            "series": [
                {"key": "best_hold", "label": "Best Hold", "color": "#C77BAE"},
            ],
        },
    ],
    "cosmic_weaver": [
        {
            "title": "Completion Rate",
            "y_max": 100,
            "y_suffix": "%",
            "series": [
                {"key": "completion_rate", "label": "Completion Rate", "color": "#7C5CE0"},
            ],
        },
        {
            "title": "Wrong Hand Attempts",
            "y_max": None,  # unbounded count - chart computes ceiling from real data
            "y_suffix": "",
            "series": [
                {"key": "wrong_hand_attempts", "label": "Wrong Hand", "color": "#D69A55"},
            ],
        },
        {
            "title": "Stars Deposited vs Dropped",
            "y_max": None,  # unbounded count - chart computes ceiling from real data
            "y_suffix": "",
            "series": [
                {"key": "stars_deposited", "label": "Deposited", "color": "#7C5CE0"},
                {"key": "stars_dropped", "label": "Dropped", "color": "#C77BAE"},
            ],
        },
    ],
}


class ProgressView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_id = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.view_stack = QStackedWidget()
        outer.addWidget(self.view_stack)

        self._build_overview_page()
        self._build_chart_page()

        self.night_sky_view = NightSkyView()
        self.night_sky_view.back_requested.connect(
            lambda: self.view_stack.setCurrentWidget(self.overview_page)
        )

        self.view_stack.addWidget(self.overview_page)
        self.view_stack.addWidget(self.chart_page)
        self.view_stack.addWidget(self.night_sky_view)
        self.view_stack.setCurrentWidget(self.overview_page)

    # ------------------------------------------------------------------
    def _build_overview_page(self):
        self.overview_page = QWidget()
        layout = QVBoxLayout(self.overview_page)
        layout.setContentsMargins(36, 40, 36, 20)
        layout.setSpacing(22)

        heading = QLabel("Your Progress")
        heading_font = QFont("Segoe UI", 22)
        heading_font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #2E2350; background: transparent;")
        layout.addWidget(heading)

        # ---- stat cards (none of these are clickable) ----
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        current_card, self.current_streak_value = make_stat_card(
            "0", "Current Streak (days)", "#7C5CE0"
        )
        best_card, self.best_streak_value = make_stat_card(
            "0", "Best Streak (days)", "#C77BAE"
        )
        total_card, self.total_sessions_value = make_stat_card(
            "0", "Total Sessions", "#8FE3E0"
        )

        stats_row.addWidget(current_card)
        stats_row.addWidget(best_card)
        stats_row.addWidget(total_card)
        layout.addLayout(stats_row)

        # ---- weekly activity, bigger ----
        self.weekly_activity = WeeklyActivityCard(dot_size=16)
        layout.addWidget(self.weekly_activity)

        # ---- per-game breakdown (these are the only clickable cards -
        # clicking opens that game's graphical progress reports) ----
        breakdown_row = QHBoxLayout()
        breakdown_row.setSpacing(20)

        bloom_card, self.bloom_sessions_value = make_stat_card(
            "0", "Bloom Forest sessions", "#C77BAE", clickable=True
        )
        bloom_card.clicked.connect(lambda: self._show_charts("bloom_forest"))

        cosmic_card, self.cosmic_sessions_value = make_stat_card(
            "0", "Cosmic Weaver sessions", "#8FE3E0", clickable=True
        )
        cosmic_card.clicked.connect(lambda: self._show_charts("cosmic_weaver"))

        # Night Sky: separate from the charts card above - opens a static,
        # full-screen view of the cumulative constellation instead of a
        # line graph. Only meaningful for Cosmic Weaver.
        night_sky_card, _night_sky_value = make_stat_card(
            "\U0001F30C", "Night Sky", "#8567E8", clickable=True
        )
        night_sky_card.clicked.connect(self._show_night_sky)

        breakdown_row.addWidget(bloom_card)
        breakdown_row.addWidget(cosmic_card)
        breakdown_row.addWidget(night_sky_card)
        layout.addLayout(breakdown_row)

        layout.addStretch()

    def _build_chart_page(self):
        self.chart_page = QWidget()
        layout = QVBoxLayout(self.chart_page)
        layout.setContentsMargins(36, 32, 36, 16)
        layout.setSpacing(6)

        back_btn = QPushButton("\u2039  Back to Progress")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #7C5CE0;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { color: #6E4FD8; }
        """)
        back_btn.clicked.connect(lambda: self.view_stack.setCurrentWidget(self.overview_page))
        layout.addWidget(back_btn)

        self.chart_heading = QLabel()
        heading_font = QFont("Segoe UI", 19)
        heading_font.setWeight(QFont.Weight.DemiBold)
        self.chart_heading.setFont(heading_font)
        self.chart_heading.setStyleSheet("color: #2E2350; background: transparent;")
        layout.addWidget(self.chart_heading)
        layout.addSpacing(8)

        # chart panels get rebuilt fresh each time _show_charts() runs,
        # since different games have a different number of charts. Wrapped
        # in a scroll area so 2, 3, or more report panels all fit without
        # ever getting cut off at the bottom of the fixed window.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: white;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: white;
                border: 1px solid rgba(124, 92, 224, 60);
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #F3EFFC;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: white;
            }
        """)
        scroll.viewport().setStyleSheet("background: transparent;")

        charts_content = QWidget()
        charts_content.setStyleSheet("background: transparent;")
        self.charts_container = QVBoxLayout(charts_content)
        self.charts_container.setSpacing(14)
        self.charts_container.addStretch()

        scroll.setWidget(charts_content)
        layout.addWidget(scroll, 1)

    # ------------------------------------------------------------------
    def _make_chart_card(self, config, history):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 225);
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 12, 18, 10)
        card_layout.setSpacing(4)

        header_row = QHBoxLayout()
        title = QLabel(config["title"])
        title_font = QFont("Segoe UI", 12)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet("color: #2E2350; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()

        # legend - only worth showing when there's more than one series
        # to tell apart (e.g. flexion vs extension on the same chart)
        if len(config["series"]) > 1:
            for s in config["series"]:
                dot = QLabel("\u25CF")
                dot.setStyleSheet(f"color: {s['color']}; background: transparent; font-size: 10px;")
                header_row.addWidget(dot)
                label = QLabel(s["label"])
                label.setStyleSheet("color: #6B5C93; background: transparent; font-size: 10px;")
                header_row.addWidget(label)
                header_row.addSpacing(8)

        card_layout.addLayout(header_row)

        chart = ProgressChart()
        chart.setFixedHeight(160)
        # FIX: previously defaulted to 100 when "y_max" was missing from a
        # config, which defeats the point of the dynamic/auto y_max path
        # in ProgressChart (y_max=None). Now the default is None, so any
        # config that omits "y_max" (or sets it to None explicitly) gets
        # a data-driven ceiling instead of silently getting 100.
        chart.load(history, config["series"], y_max=config.get("y_max"),
                   y_suffix=config.get("y_suffix", ""))
        card_layout.addWidget(chart)

        return card

    def _show_charts(self, game_id):
        while self.charts_container.count():
            item = self.charts_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        game_name = get_game_display_name(game_id)
        self.chart_heading.setText(f"{game_name} \u2014 Progress Reports")

        history = get_session_history(self._user_id, game_id=game_id, limit=7)
        configs = GAME_CHART_CONFIGS.get(game_id, [])

        if not configs:
            empty = QLabel("No reports defined for this game yet.")
            empty.setStyleSheet("color: #6B5C93; background: transparent; font-size: 12px;")
            self.charts_container.addWidget(empty)
        else:
            for config in configs:
                self.charts_container.addWidget(self._make_chart_card(config, history))

        self.charts_container.addStretch()
        self.view_stack.setCurrentWidget(self.chart_page)

    def _show_night_sky(self):
        self.night_sky_view.load(self._user_id)
        self.view_stack.setCurrentWidget(self.night_sky_view)

    # ------------------------------------------------------------------
    def refresh_for_user(self, user_id):
        """Call this whenever the tab should show fresh data - both when
        the user navigates here manually and right after login."""
        self._user_id = user_id

        self.current_streak_value.setText(str(get_current_streak(user_id)))
        self.best_streak_value.setText(str(get_best_streak(user_id)))
        self.total_sessions_value.setText(str(get_total_sessions(user_id)))

        self.weekly_activity.set_sessions(get_weekly_session_days(user_id))

        counts = get_game_session_counts(user_id)
        self.bloom_sessions_value.setText(str(counts.get("bloom_forest", 0)))
        self.cosmic_sessions_value.setText(str(counts.get("cosmic_weaver", 0)))

        # if the chart page happens to be open when this refreshes (e.g.
        # after finishing a game elsewhere), go back to the overview
        # rather than showing a now-stale chart.
        self.view_stack.setCurrentWidget(self.overview_page)

    # ------------------------------------------------------------------
    # Manual setters, kept for any direct/manual overrides you still want
    def set_current_streak(self, days):
        self.current_streak_value.setText(str(days))

    def set_best_streak(self, days):
        self.best_streak_value.setText(str(days))

    def set_total_sessions(self, count):
        self.total_sessions_value.setText(str(count))

    def set_game_sessions(self, bloom_forest_count, cosmic_weaver_count):
        self.bloom_sessions_value.setText(str(bloom_forest_count))
        self.cosmic_sessions_value.setText(str(cosmic_weaver_count))