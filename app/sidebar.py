"""
Sidebar
---------
Persistent left-hand navigation, solid purple, matching the reference
layout: brand mark, nav items (Home / Games / Progress) with a chevron on
whichever one is active, a streak card, and a user row with a settings
icon. Emits nav_changed("home" | "games" | "progress") on click.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor

NAV_ITEMS = [
    ("home", "\U0001F3E0", "Home"),
    ("games", "\U0001F3AE", "Games"),
    ("progress", "\U0001F4C8", "Progress"),
]


class Sidebar(QFrame):

    nav_changed = pyqtSignal(str)
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self._nav_buttons = {}
        self._build_ui()
        self.set_active("home")

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#8567E8"))
        gradient.setColorAt(1.0, QColor("#6B4FD1"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(self.rect(), 22, 22)
        super().paintEvent(event)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(0)

        # ---- brand ----
        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)
        logo = QLabel("\U0001F300")
        logo.setStyleSheet("background: transparent; font-size: 18px;")
        brand_row.addWidget(logo)
        brand_label = QLabel("REHABVERSE")
        brand_font = QFont("Segoe UI", 10)
        brand_font.setWeight(QFont.Weight.DemiBold)
        brand_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        brand_label.setFont(brand_font)
        brand_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        brand_row.addWidget(brand_label)
        brand_row.addStretch()
        layout.addLayout(brand_row)
        layout.addSpacing(30)

        # ---- nav buttons ----
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for key, icon, label in NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(44)
            btn.setStyleSheet(self._nav_button_style())
            btn.clicked.connect(lambda _, k=key: self._on_nav_clicked(k))
            self._set_nav_text(btn, icon, label, active=(key == "home"))
            self._btn_group.addButton(btn)
            self._nav_buttons[key] = (btn, icon, label)
            layout.addWidget(btn)
            layout.addSpacing(6)

        layout.addSpacing(18)
        layout.addStretch()

        # ---- streak card ----
        streak_card = QFrame()
        streak_card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 14px;
            }
        """)
        streak_layout = QVBoxLayout(streak_card)
        streak_layout.setContentsMargins(14, 12, 14, 12)
        streak_layout.setSpacing(2)

        streak_title = QLabel("Streak")
        streak_title.setStyleSheet("color: #8A7CB0; background: transparent; font-size: 11px;")
        streak_layout.addWidget(streak_title)

        streak_row = QHBoxLayout()
        streak_row.setSpacing(6)
        fire = QLabel("\U0001F525")
        fire.setStyleSheet("background: transparent; font-size: 16px;")
        streak_row.addWidget(fire)
        self.streak_value = QLabel("5")
        streak_value_font = QFont("Segoe UI", 15)
        streak_value_font.setWeight(QFont.Weight.Bold)
        self.streak_value.setFont(streak_value_font)
        self.streak_value.setStyleSheet("color: #3D2E63; background: transparent;")
        streak_row.addWidget(self.streak_value)
        days_label = QLabel("Days")
        days_label.setStyleSheet("color: #8A7CB0; background: transparent; font-size: 12px;")
        streak_row.addWidget(days_label)
        streak_row.addStretch()
        streak_layout.addLayout(streak_row)

        keep_going = QLabel("Keep going!")
        keep_going.setStyleSheet("color: #A97FD8; background: transparent; font-size: 10px;")
        streak_layout.addWidget(keep_going)

        layout.addWidget(streak_card)
        layout.addSpacing(12)

        # ---- user row ----
        user_row = QFrame()
        user_row.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 14px;
            }
        """)
        user_layout = QHBoxLayout(user_row)
        user_layout.setContentsMargins(10, 8, 10, 8)
        user_layout.setSpacing(8)

        avatar = QLabel("\U0001F464")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("""
            background-color: #E4D6F5;
            border-radius: 15px;
            font-size: 14px;
        """)
        user_layout.addWidget(avatar)

        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        self.user_name_label = QLabel("Ipsita")
        name_font = QFont("Segoe UI", 11)
        name_font.setWeight(QFont.Weight.DemiBold)
        self.user_name_label.setFont(name_font)
        self.user_name_label.setStyleSheet("color: #3D2E63; background: transparent;")
        name_col.addWidget(self.user_name_label)
        member_label = QLabel("Member")
        member_label.setStyleSheet("color: #A79BC7; background: transparent; font-size: 10px;")
        name_col.addWidget(member_label)
        user_layout.addLayout(name_col)
        user_layout.addStretch()

        settings_btn = QPushButton("\u2699")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setFixedSize(24, 24)
        settings_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #8A7CB0;
                font-size: 14px;
            }
            QPushButton:hover { color: #7C5CE0; }
        """)
        settings_btn.clicked.connect(self.settings_clicked.emit)
        user_layout.addWidget(settings_btn)

        layout.addWidget(user_row)

    def _set_nav_text(self, btn, icon, label, active):
        chevron = "   \u203A" if active else ""
        btn.setText(f"  {icon}   {label}{chevron}")

    def _nav_button_style(self):
        return """
            QPushButton {
                text-align: left;
                border: none;
                border-radius: 12px;
                color: rgba(255, 255, 255, 190);
                font-size: 13px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 18);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 32);
                color: #FFFFFF;
                font-weight: 600;
            }
        """

    # ------------------------------------------------------------------
    def _on_nav_clicked(self, key):
        self.set_active(key)
        self.nav_changed.emit(key)

    def set_active(self, key):
        if key not in self._nav_buttons:
            return
        for k, (btn, icon, label) in self._nav_buttons.items():
            is_active = (k == key)
            btn.setChecked(is_active)
            self._set_nav_text(btn, icon, label, active=is_active)

    def set_user_name(self, name):
        self.user_name_label.setText(name)

    def set_streak(self, days):
        self.streak_value.setText(str(days))