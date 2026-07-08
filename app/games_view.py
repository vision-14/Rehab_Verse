"""
Games View
------------
Shows the two rehab games as themed cards, each with its own decorative
painting, a short description of what the game trains, and a Start Game
button. Emits game_selected("bloom_forest" | "cosmic_weaver") when a Start
button is clicked - hook that up to whatever actually launches the game.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QLinearGradient

from decorative_shapes import draw_flower, draw_star_field, draw_constellation


class GameCard(QFrame):
    """Base themed card. Subclasses set colors/copy and override
    _paint_decoration() for the background motif."""

    start_clicked = pyqtSignal(str)

    game_id = "game"
    icon = "\U0001F3AE"
    title_text = "Game"
    badge_text = "REHAB"
    description_text = ""
    bg_top = "#FFFFFF"
    bg_bottom = "#FFFFFF"
    badge_color = "#7C5CE0"
    button_grad = ("#7C5CE0", "#B983C9")
    title_color = "#2E2350"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 340)
        self._t = 0.0
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._build_ui()

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
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path_rect = self.rect()
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(self.bg_top))
        gradient.setColorAt(1.0, QColor(self.bg_bottom))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(path_rect, 20, 20)

        painter.save()
        painter.setClipRect(path_rect)
        self._paint_decoration(painter, w, h)
        painter.restore()

        super().paintEvent(event)

    def _paint_decoration(self, painter, w, h):
        pass

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 20)
        layout.setSpacing(10)

        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("background: transparent; font-size: 30px;")
        layout.addWidget(icon_label)

        title = QLabel(self.title_text)
        title_font = QFont("Segoe UI", 17)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {self.title_color}; background: transparent;")
        layout.addWidget(title)

        badge = QLabel(self.badge_text)
        badge_font = QFont("Segoe UI", 8)
        badge_font.setWeight(QFont.Weight.DemiBold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        badge.setFont(badge_font)
        badge.setFixedHeight(20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            color: white;
            background-color: {self.badge_color};
            border-radius: 10px;
            padding: 0px 10px;
        """)
        badge.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addSpacing(4)
        desc = QLabel(self.description_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(45, 35, 80, 190); background: transparent; font-size: 12px;")
        layout.addWidget(desc)

        layout.addStretch()

        start_btn = QPushButton("Start Game  \u25B6")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setFixedHeight(40)
        c1, c2 = self.button_grad
        start_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 600;
                color: white;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, stop:0 {c1}, stop:1 {c2}
                );
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, stop:0 {c1}, stop:1 {c1}
                );
            }}
        """)
        start_btn.clicked.connect(lambda: self.start_clicked.emit(self.game_id))
        layout.addWidget(start_btn)


class BloomForestCard(GameCard):
    game_id = "bloom_forest"
    icon = "\U0001F338"
    title_text = "Bloom Forest"
    badge_text = "WRIST REHAB"
    description_text = (
        "Guide gentle wrist rotations and flexions to help flowers bloom "
        "across the forest. Builds range of motion and control at a "
        "comfortable, encouraging pace."
    )
    bg_top = "#FCEFF7"
    bg_bottom = "#F7E1EF"
    badge_color = "#C77BAE"
    button_grad = ("#C77BAE", "#B983C9")
    title_color = "#5C2E4C"

    def _paint_decoration(self, painter, w, h):
        draw_flower(painter, w - 34, h - 30, 30, "#D79FC4", alpha=140)
        draw_flower(painter, w - 74, h - 55, 22, "#E3B6D6", alpha=120)
        draw_flower(painter, 30, h - 22, 18, "#E3B6D6", alpha=90)


class CosmicWeaverCard(GameCard):
    game_id = "cosmic_weaver"
    icon = "\U0001F30C"
    title_text = "Cosmic Weaver"
    badge_text = "NEURO + MOTOR REHAB"
    description_text = (
        "Trace glowing constellations with coordinated fist and finger "
        "movements. Trains fine motor control and neuro-motor coordination "
        "through focused, guided patterns."
    )
    bg_top = "#2A2149"
    bg_bottom = "#1B1533"
    badge_color = "#8FE3E0"
    button_grad = ("#8FE3E0", "#B8A3EF")
    title_color = "#F1EEFB"

    def _paint_decoration(self, painter, w, h):
        draw_star_field(painter, w, h, count=22, seed=4, t=self._t,
                         color=QColor(200, 210, 255))
        points = [
            QPointF(w * 0.68, h * 0.14), QPointF(w * 0.82, h * 0.20),
            QPointF(w * 0.78, h * 0.30), QPointF(w * 0.62, h * 0.28),
        ]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        draw_constellation(painter, points, edges, t=self._t)


class GamesView(QWidget):

    game_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 20)
        layout.setSpacing(18)

        heading = QLabel("Choose Your Game")
        heading_font = QFont("Segoe UI", 22)
        heading_font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #2E2350; background: transparent;")
        layout.addWidget(heading)

        subheading = QLabel("Pick a session that matches what you're working on today.")
        subheading.setStyleSheet("color: rgba(45, 35, 80, 160); background: transparent; font-size: 12px;")
        layout.addWidget(subheading)
        layout.addSpacing(10)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(48)

        self.bloom_card = BloomForestCard()
        self.cosmic_card = CosmicWeaverCard()
        self.bloom_card.start_clicked.connect(self.game_selected.emit)
        self.cosmic_card.start_clicked.connect(self.game_selected.emit)

        cards_row.addStretch()
        cards_row.addWidget(self.bloom_card)
        cards_row.addWidget(self.cosmic_card)
        cards_row.addStretch()

        layout.addLayout(cards_row)
        layout.addStretch()

        # description labels on the dark cosmic card need light text -
        # override after construction since the base class styles them dark
        for lbl in self.cosmic_card.findChildren(QLabel):
            style = lbl.styleSheet()
            if "45, 35, 80" in style:  # this was the description label
                lbl.setStyleSheet("color: rgba(230, 228, 250, 190); background: transparent; font-size: 12px;")