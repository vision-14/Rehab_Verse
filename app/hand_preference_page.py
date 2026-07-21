"""
Hand Preference Page
-----------------------
Shown after "Let's Begin" on the instructions page, before Cosmic Weaver
actually launches - asks Left / Right / Both, same dark starry cosmic
theme as the splash/login screens (reuses CosmicPage, the same base
class those use).

Only Cosmic Weaver needs this (Bloom Forest has no hand-preference
concept) - see dashboard_page.py for where this gets skipped for other
games.

Emits:
    confirmed(game_id: str, hand_pref: str)
        -> hand_pref is one of "left", "right", "both"
    back_requested()
        -> user backed out instead of confirming
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from cosmic_background import CosmicPage

HAND_OPTIONS = [
    ("left", "\U0001F91A", "Left Hand"),
    ("right", "\u270B", "Right Hand"),
    ("both", "\U0001F64C", "Both Hands"),
]


class HandPreferencePage(CosmicPage):

    confirmed = pyqtSignal(str, str)
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._game_id = None
        self._selected = "both"
        self._option_buttons = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(self)
        card.setObjectName("handPrefCard")
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QFrame#handPrefCard {
                background-color: rgba(255, 255, 255, 18);
                border: 1px solid rgba(200, 190, 255, 55);
                border-radius: 22px;
            }
        """)
        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 32, 36, 30)
        card_layout.setSpacing(4)

        # ---- back link ----
        back_row = QHBoxLayout()
        back_btn = QPushButton("\u2039  Back")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #8FE3E0;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { color: #B8A3EF; }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        back_row.addWidget(back_btn)
        back_row.addStretch()
        card_layout.addLayout(back_row)
        card_layout.addSpacing(6)

        # ---- brand mark ----
        brand = QLabel("REHABVERSE")
        brand_font = QFont("Segoe UI", 10)
        brand_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.6)
        brand_font.setWeight(QFont.Weight.DemiBold)
        brand.setFont(brand_font)
        brand.setStyleSheet("color: #B8A3EF; background: transparent;")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(brand)
        card_layout.addSpacing(14)

        # ---- heading ----
        heading = QLabel("Choose Your Hand")
        heading_font = QFont("Segoe UI", 21)
        heading_font.setWeight(QFont.Weight.Light)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #F1EEFB; background: transparent;")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(heading)

        subheading = QLabel("Which hand would you like to train today?")
        subheading.setStyleSheet("color: rgba(210, 205, 235, 170); background: transparent;")
        subheading.setFont(QFont("Segoe UI", 10))
        subheading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subheading)
        card_layout.addSpacing(24)

        # ---- three option cards ----
        options_row = QHBoxLayout()
        options_row.setSpacing(12)
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for key, icon, label in HAND_OPTIONS:
            btn = QPushButton(f"{icon}\n{label}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(110, 96)
            btn.setStyleSheet(self._option_style())
            btn.clicked.connect(lambda _, k=key: self._select(k))
            self._btn_group.addButton(btn)
            self._option_buttons[key] = btn
            options_row.addWidget(btn)

        card_layout.addLayout(options_row)
        card_layout.addSpacing(26)

        # ---- confirm button ----
        confirm_btn = QPushButton("Continue  \u203A")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(42)
        confirm_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                color: #1B1030;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8FE3E0, stop:0.5 #B8A3EF, stop:1 #E3A6E8
                );
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7FD8D4, stop:0.5 #A891E8, stop:1 #DB94E0
                );
            }
        """)
        confirm_btn.clicked.connect(
            lambda: self.confirmed.emit(self._game_id, self._selected)
        )
        card_layout.addWidget(confirm_btn)

        self._select("both")  # sensible default, matches the controller's own fallback

    def _option_style(self):
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 14px;
                color: #E4E0F7;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 26);
            }
            QPushButton:checked {
                background-color: rgba(184, 163, 239, 45);
                border: 1px solid #B8A3EF;
            }
        """

    # ------------------------------------------------------------------
    def _select(self, key):
        self._selected = key
        if key in self._option_buttons:
            self._option_buttons[key].setChecked(True)

    def load(self, game_id):
        self._game_id = game_id
        self._select("both")