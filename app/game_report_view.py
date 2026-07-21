"""
Game Report View
------------------
Lives in the dashboard's sidebar as its own tab ("Report"), next to Home /
Games / Progress. Shows the most recent session's real metrics for
whichever game you toggle to, grouped into labeled sections - just cards,
no constellation scene (that lives in the Progress tab's dedicated
"Night Sky" view now instead - see night_sky_view.py).

Everything below the toggle row lives inside a scroll area, so no matter
how many sections/cards a game has, content never overlaps or clips
against the fixed window height - it scrolls instead.

Call load(user_id, game_id) whenever this should show fresh data - the
dashboard does this both when the user clicks "Report" in the sidebar,
and automatically the moment a game process exits.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QButtonGroup, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from stat_card import make_stat_card
from session_data import get_latest_session_summary, get_game_display_name

GAME_IDS = ["bloom_forest", "cosmic_weaver"]

# Each game's report is a list of SECTIONS (title + card defs), instead of
# one flat grid - keeps related numbers grouped and reads more like an
# actual report than a wall of stat boxes.
# Card def format: (summary_key, suffix, decimals, label, color)
GAME_REPORT_SECTIONS = {
    "bloom_forest": [
        {
            "title": "Session Overview",
            "cards": [
                ("accuracy", "%", 1, "Accuracy", "#7C5CE0"),
                ("completion_rate", "%", 1, "Completion Rate", "#C77BAE"),
                ("session_duration", "s", 0, "Session Duration", "#8FE3E0"),
            ],
        },
        {
            "title": "Range of Motion",
            "cards": [
                ("rom", "\u00b0", 1, "Overall ROM", "#7C5CE0"),
                ("flexion_rom", "\u00b0", 1, "Flexion ROM", "#C77BAE"),
                ("extension_rom", "\u00b0", 1, "Extension ROM", "#8FE3E0"),
                ("best_hold", "s", 1, "Best Hold", "#7C5CE0"),
                ("avg_reach_time", "s", 1, "Avg Reach Time", "#C77BAE"),
            ],
        },
        {
            "title": "Bloom Results",
            "cards": [
                ("flowers", "", 0, "\U0001F338 Flowers", "#C77BAE"),
                ("buds", "", 0, "\U0001F33F Buds", "#8FE3E0"),
                ("leaves", "", 0, "\U0001F343 Leaves", "#7C5CE0"),
            ],
        },
    ],
    "cosmic_weaver": [
        {
            "title": "Session Overview",
            "cards": [
                ("score", "", 0, "Score", "#7C5CE0"),
                ("accuracy", "%", 1, "Accuracy", "#7C5CE0"),
                ("completion_rate", "%", 1, "Completion Rate", "#C77BAE"),
                ("session_duration", "s", 0, "Session Duration", "#8FE3E0"),
            ],
        },
        {
            "title": "Star Activity",
            "cards": [
                ("stars_deposited", "", 0, "Stars Deposited", "#8FE3E0"),
                ("stars_dropped", "", 0, "Stars Dropped", "#C77BAE"),
                ("nebula_collected", "", 0, "Nebula Collected", "#7C5CE0"),
                ("best_streak", "", 0, "Best Streak", "#C77BAE"),
                ("wrong_hand_attempts", "", 0, "Wrong Hand Attempts", "#D69A55"),
            ],
        },
    ],
}

CARD_COLUMNS = 3


def _fmt(value, suffix="", decimals=1):
    if value is None:
        return "\u2014"  # em dash for "no data yet"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return f"{value}{suffix}"


class GameReportView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_id = None
        self._active_game_id = GAME_IDS[0]
        self._toggle_buttons = {}
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 40, 36, 16)
        outer.setSpacing(6)

        heading = QLabel("Session Report")
        heading_font = QFont("Segoe UI", 22)
        heading_font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #2E2350; background: transparent;")
        outer.addWidget(heading)

        self.subheading_label = QLabel("Your most recent results for each game")
        self.subheading_label.setStyleSheet("color: rgba(45, 35, 80, 160); background: transparent; font-size: 12px;")
        outer.addWidget(self.subheading_label)
        outer.addSpacing(16)

        # ---- game toggle (stays fixed above the scroll area) ----
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(10)
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for game_id in GAME_IDS:
            btn = QPushButton(get_game_display_name(game_id))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.setStyleSheet(self._toggle_style())
            btn.clicked.connect(lambda _, g=game_id: self._on_toggle(g))
            self._btn_group.addButton(btn)
            self._toggle_buttons[game_id] = btn
            toggle_row.addWidget(btn)
        toggle_row.addStretch()
        outer.addLayout(toggle_row)
        outer.addSpacing(14)

        # ---- everything below scrolls, so N sections/cards never
        # overlap or clip against the fixed window height ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(self._scrollbar_style())
        scroll.viewport().setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 4, 8)
        self.content_layout.setSpacing(18)

        # sections get rebuilt fresh on every _render() call
        self.sections_container = QVBoxLayout()
        self.sections_container.setSpacing(18)
        self.content_layout.addLayout(self.sections_container)

        # ---- empty state ----
        self.empty_label = QLabel(
            "No sessions recorded for this game yet - play a round and it'll show up here."
        )
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("""
            color: #6B5C93;
            background-color: rgba(255, 255, 255, 200);
            border-radius: 16px;
            padding: 20px;
            font-size: 13px;
        """)
        self.empty_label.hide()
        self.content_layout.addWidget(self.empty_label)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._toggle_buttons[self._active_game_id].setChecked(True)

    def _toggle_style(self):
        return """
            QPushButton {
                border: 1px solid rgba(124, 92, 224, 90);
                border-radius: 19px;
                padding: 0 18px;
                color: #7C5CE0;
                font-size: 12px;
                font-weight: 600;
                background-color: rgba(255, 255, 255, 210);
            }
            QPushButton:hover {
                background-color: rgba(124, 92, 224, 25);
            }
            QPushButton:checked {
                background-color: #7C5CE0;
                color: white;
                border: 1px solid #7C5CE0;
            }
        """

    def _scrollbar_style(self):
        return """
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(124, 92, 224, 90);
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(124, 92, 224, 140);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """

    def _section_title_style(self):
        return "color: #6B5C93; background: transparent; font-size: 12px; font-weight: 600; letter-spacing: 1px;"

    # ------------------------------------------------------------------
    def load(self, user_id, game_id=None):
        """Call this whenever the view should show fresh data - both when
        the user navigates here manually and right after a game exits."""
        self._user_id = user_id
        if game_id and game_id in self._toggle_buttons:
            self._active_game_id = game_id
        self._toggle_buttons[self._active_game_id].setChecked(True)
        self._refresh()

    def _on_toggle(self, game_id):
        self._active_game_id = game_id
        self._refresh()

    def _refresh(self):
        summary = None
        if self._user_id:
            summary = get_latest_session_summary(self._user_id, self._active_game_id)
        self._render(summary)

    def _clear_layout(self, layout):
        """Recursively removes and deletes every widget in a layout tree,
        including widgets nested inside child layouts (e.g. a QGridLayout
        of cards sitting inside a QVBoxLayout section). The previous
        version only cleared one level deep, so a section's title label
        was removed but its card grid (one level further in) never was -
        old cards stayed alive and rendered UNDERNEATH the new ones,
        which is exactly the overlapping/bleeding-through text seen in
        the screenshots (old "Score"/"Accuracy" text showing through the
        new cards)."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _make_section(self, title, card_defs, summary):
        section = QVBoxLayout()
        section.setSpacing(10)

        title_label = QLabel(title.upper())
        title_label.setStyleSheet(self._section_title_style())
        section.addWidget(title_label)

        grid = QGridLayout()
        grid.setSpacing(16)
        for i, (key, suffix, decimals, label, color) in enumerate(card_defs):
            card, _value_label = make_stat_card(
                _fmt(summary.get(key), suffix, decimals), label, color
            )
            row, col = divmod(i, CARD_COLUMNS)
            grid.addWidget(card, row, col)
        section.addLayout(grid)

        return section

    def _render(self, summary):
        self._clear_layout(self.sections_container)

        if not summary:
            game_name = get_game_display_name(self._active_game_id)
            self.subheading_label.setText(f"No {game_name} sessions yet")
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.subheading_label.setText(
            f"{summary.get('game_name', 'Game')} \u2014 most recent session"
        )

        sections = GAME_REPORT_SECTIONS.get(self._active_game_id, [])
        for section_def in sections:
            section_layout = self._make_section(
                section_def["title"], section_def["cards"], summary
            )
            self.sections_container.addLayout(section_layout)