"""
Home View
-----------
The dashboard's "Home" content, laid out like the reference: a hero card
on the left (date, greeting, a short streak-based blurb, a Play Now
button, decorative sparkles + wave) and a right-hand column stacking the
daily motivation quote, the weekly activity strip, and a Quick Play
shortcut into the Games screen. No scheduling anywhere - Play Now and
Quick Play both just jump straight to Games.
"""

import math
from datetime import date
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QFont, QPainter, QLinearGradient, QRadialGradient, QColor, QPainterPath

from decorative_shapes import draw_star_field
from session_data import get_current_streak, get_weekly_session_days, get_random_quote
from weekly_activity import WeeklyActivityCard


# ----------------------------------------------------------------------
class DashboardHeroCard(QFrame):
    """Left-hand hero panel: dashboard label + bell, date, greeting,
    streak blurb, Play Now button, on a soft decorative background."""

    bell_clicked = pyqtSignal()
    play_now_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_name = "there"
        self._build_ui()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        gradient = QLinearGradient(0, 0, w * 0.3, h)
        gradient.setColorAt(0.0, QColor("#EDE6FA"))
        gradient.setColorAt(1.0, QColor("#E3D8F5"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 26, 26)

        painter.save()
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 26, 26)
        painter.setClipPath(path)

        glow = QRadialGradient(QPointF(w * 0.8, h * 0.24), w * 0.24)
        c1 = QColor("#C9B7EC")
        c1.setAlpha(90)
        c2 = QColor("#C9B7EC")
        c2.setAlpha(0)
        glow.setColorAt(0.0, c1)
        glow.setColorAt(1.0, c2)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(w * 0.8, h * 0.24), w * 0.24, w * 0.24)

        draw_star_field(painter, w, h * 0.7, count=16, seed=9, t=0.0,
                         color=QColor(150, 130, 200))

        wave_path = QPainterPath()
        base_y = h * 0.87
        wave_path.moveTo(0, h)
        wave_path.lineTo(0, base_y)
        steps = 20
        for i in range(steps + 1):
            x = w * i / steps
            y = base_y + h * 0.025 * math.sin(i * 0.8)
            wave_path.lineTo(x, y)
        wave_path.lineTo(w, h)
        wave_path.closeSubpath()
        wave_color = QColor("#CBB8ED")
        wave_color.setAlpha(150)
        painter.setBrush(wave_color)
        painter.drawPath(wave_path)

        painter.restore()
        super().paintEvent(event)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        kicker = QLabel("DASHBOARD")
        kicker_font = QFont("Segoe UI", 9)
        kicker_font.setWeight(QFont.Weight.DemiBold)
        kicker_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        kicker.setFont(kicker_font)
        kicker.setStyleSheet("color: #8A7CB0; background: transparent;")
        top_row.addWidget(kicker)
        top_row.addStretch()

        bell_btn = QPushButton("\U0001F514")
        bell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bell_btn.setFixedSize(34, 34)
        bell_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 160);
                border-radius: 17px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 220); }
        """)
        bell_btn.clicked.connect(self.bell_clicked.emit)
        top_row.addWidget(bell_btn)
        layout.addLayout(top_row)

        layout.addStretch(2)

        self.date_label = QLabel()
        self.date_label.setStyleSheet("color: #8A7CB0; background: transparent; font-size: 12px;")
        layout.addWidget(self.date_label)

        self.greeting_label = QLabel()
        greeting_font = QFont("Segoe UI", 27)
        greeting_font.setWeight(QFont.Weight.Bold)
        self.greeting_label.setFont(greeting_font)
        self.greeting_label.setStyleSheet("color: #2E2350; background: transparent;")
        layout.addWidget(self.greeting_label)

        self.name_label = QLabel()
        self.name_label.setFont(greeting_font)
        self.name_label.setStyleSheet("color: #7C5CE0; background: transparent;")
        layout.addWidget(self.name_label)

        layout.addSpacing(10)
        self.blurb_label = QLabel()
        self.blurb_label.setWordWrap(True)
        self.blurb_label.setStyleSheet("color: #6B5C93; background: transparent; font-size: 13px;")
        layout.addWidget(self.blurb_label)

        layout.addSpacing(14)
        play_btn = QPushButton("Play Now  \u203A")
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setFixedSize(180, 42)
        play_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 21px;
                color: white;
                font-size: 13px;
                font-weight: 600;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, stop:0 #7C5CE0, stop:1 #9B7BE8
                );
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, stop:0 #6E4FD8, stop:1 #8C6BDD
                );
            }
        """)
        play_btn.clicked.connect(self.play_now_clicked.emit)
        layout.addWidget(play_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addStretch(3)

        self._refresh_greeting()

    # ------------------------------------------------------------------
    def set_user_name(self, name):
        self._user_name = name or "there"
        self._refresh_greeting()

    def _refresh_greeting(self):
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good Morning,"
        elif hour < 17:
            greeting = "Good Afternoon,"
        else:
            greeting = "Good Evening,"
        self.greeting_label.setText(greeting)
        self.name_label.setText(f"{self._user_name} \U0001F338")
        self.date_label.setText(date.today().strftime("%A, %B ") + str(date.today().day))

        streak = get_current_streak()
        self.blurb_label.setText(
            f"You're on a {streak}-day streak. Every session is building real strength \u2014 keep going!"
        )


# ----------------------------------------------------------------------
class QuoteCard(QFrame):
    """Motivation quote card. Shows one line from the pool, wrapped in real
    quotation marks, chosen at random - with a shuffle button to see another."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_quote = None
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 225);
                border-radius: 18px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(8)

        icon = QLabel("\U0001F463")  # footprints
        icon_font = QFont("Segoe UI", 16)
        icon.setFont(icon_font)
        icon.setStyleSheet("color: #C9B7EC; background: transparent;")
        layout.addWidget(icon)

        self.quote_label = QLabel()
        self.quote_label.setWordWrap(True)
        quote_font = QFont("Segoe UI", 13)
        quote_font.setWeight(QFont.Weight.DemiBold)
        self.quote_label.setFont(quote_font)
        self.quote_label.setStyleSheet("color: #3D2E63; background: transparent;")
        layout.addWidget(self.quote_label)
        layout.addStretch()

        footer_row = QHBoxLayout()
        label = QLabel("DAILY MOTIVATION")
        label_font = QFont("Segoe UI", 8)
        label_font.setWeight(QFont.Weight.DemiBold)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        label.setFont(label_font)
        label.setStyleSheet("color: #A79BC7; background: transparent;")
        footer_row.addWidget(label)
        footer_row.addStretch()

        shuffle_btn = QPushButton("\u27F3")
        shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        shuffle_btn.setFixedSize(30, 30)
        shuffle_btn.setToolTip("Show another")
        shuffle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 92, 224, 30);
                border-radius: 15px;
                color: #7C5CE0;
                font-size: 14px;
            }
            QPushButton:hover { background-color: rgba(124, 92, 224, 55); }
        """)
        shuffle_btn.clicked.connect(self.show_new_quote)
        footer_row.addWidget(shuffle_btn)
        layout.addLayout(footer_row)

        self.show_new_quote()

    def show_new_quote(self):
        self._current_quote = get_random_quote(exclude=self._current_quote)
        self.quote_label.setText(f"\u201C{self._current_quote}\u201D")


# ----------------------------------------------------------------------
class QuickPlayCard(QFrame):
    """Replaces a 'next scheduled session' card with a direct shortcut
    into the Games screen - no scheduling, just a quick jump-in point."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: #7C5CE0;
                border-radius: 18px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        icon = QLabel("\U0001F3AE")
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("""
            background-color: rgba(255, 255, 255, 35);
            border-radius: 12px;
            font-size: 18px;
        """)
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        label = QLabel("QUICK PLAY")
        label_font = QFont("Segoe UI", 8)
        label_font.setWeight(QFont.Weight.DemiBold)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        label.setFont(label_font)
        label.setStyleSheet("color: rgba(255, 255, 255, 190); background: transparent;")
        text_col.addWidget(label)

        subtitle = QLabel("Jump into a session")
        subtitle_font = QFont("Segoe UI", 12)
        subtitle_font.setWeight(QFont.Weight.DemiBold)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: white; background: transparent;")
        text_col.addWidget(subtitle)
        layout.addLayout(text_col)
        layout.addStretch()

        chevron = QLabel("\u203A")
        chevron.setStyleSheet("color: white; background: transparent; font-size: 18px;")
        layout.addWidget(chevron)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ----------------------------------------------------------------------
class HomeView(QWidget):

    play_requested = pyqtSignal()  # bubbles up: main dashboard should switch to Games

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.hero_card = DashboardHeroCard()
        self.hero_card.play_now_clicked.connect(self.play_requested.emit)
        layout.addWidget(self.hero_card, 3)

        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        self.quote_card = QuoteCard()
        right_col.addWidget(self.quote_card, 2)

        self.weekly_activity = WeeklyActivityCard(dot_size=13)
        self.weekly_activity.set_sessions(get_weekly_session_days())
        right_col.addWidget(self.weekly_activity, 2)

        self.quick_play_card = QuickPlayCard()
        self.quick_play_card.clicked.connect(self.play_requested.emit)
        right_col.addWidget(self.quick_play_card)

        right_container = QWidget()
        right_container.setLayout(right_col)
        right_container.setFixedWidth(300)
        layout.addWidget(right_container, 0)

    # ------------------------------------------------------------------
    def set_user_name(self, name):
        self.hero_card.set_user_name(name)