"""
Instructions Page
--------------------
"How to play" carousel shown before a game launches - one step at a time,
with left/right arrow navigation and a dot progress indicator, in the
same light bloom theme as the rest of the dashboard. Each step gets a
large icon "badge" instead of a tiny inline one, so there's plenty of
room for the description text (the earlier all-steps-stacked layout was
cramming 2-line descriptions into rows that were too short, which clipped
the text - this fixes that by giving each step the whole card).

Lives inside the dashboard's content_stack like Home/Games/Report. Call
load(game_id) to populate it, then the dashboard crossfades to it.
Emits play_confirmed(game_id) when the person clicks through to actually
start the game, or back_requested() if they back out to Games instead.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Content for each game's instructions. Add cosmic_weaver's real steps
# here once its gameplay loop is finalized - the page itself is generic.
GAME_INSTRUCTIONS = {
    "bloom_forest": {
        "title": "How to Play: Bloom Forest",
        "subtitle": "Wrist rehab, guided step by step",
        "steps": [
            {
                "icon": "\u270B",
                "accent": "#7C5CE0",
                "title": "Press \u2018C\u2019 to Calibrate",
                "desc": "Keep your arm straight and your hand horizontal, like a pledge. Press C to set your neutral position.",
            },
            {
                "icon": "\U0001F3AF",
                "accent": "#C77BAE",
                "title": "Reach the Target Angle",
                "desc": "The game shows you a target angle. Move your wrist up or down to reach it.",
            },
            {
                "icon": "\u23F3",
                "accent": "#8FE3E0",
                "title": "Hold Steady",
                "desc": "Stay at the target and hold still. The bar fills as you hold \u2014 difficulty adapts to your progress over time.",
            },
            {
                "icon": "\U0001F338",
                "accent": "#7C5CE0",
                "title": "Grow Your Flower",
                "desc": "Your stability while holding decides the bloom: steady earns a full flower, shaky earns a bud, very shaky earns a leaf.",
            },
        ],
        "footer_title": "Round Complete!",
        "footer_desc": "Your results are saved automatically, and the next target appears.",
    },
    "cosmic_weaver": {
        "title": "How to Play: Cosmic Weaver",
        "subtitle": "Neuro + motor rehab, guided step by step",
        "steps": [
            {
                "icon": "\U0001F449",
                "accent": "#4B3B8C",
                "title": "Follow the Hand Cue",
                "desc": "The game calls out Left or Right. Only that hand's movement counts \u2014 keep the other one relaxed and still.",
            },
            {
                "icon": "\u270A",
                "accent": "#C77BAE",
                "title": "Reach & Grip the Star",
                "desc": "Move toward a glowing star and grip it firmly \u2014 your grip strength is what registers the grab.",
            },
            {
                "icon": "\U0001F52E",
                "accent": "#8FE3E0",
                "title": "Carry It to the Energy Center",
                "desc": "Once you've got it, carry the star over to the energy center to bank it before letting go.",
            },
            {
                "icon": "\u23F3",
                "accent": "#7C5CE0",
                "title": "Beat the Fade",
                "desc": "Stars only stay lit for a short time \u2014 grab and deliver before they fade away.",
            },
            {
                "icon": "\u2728",
                "accent": "#9B59B6",
                "title": "Catch the Nebula Stars",
                "desc": "Purple nebula stars are worth +2 points \u2014 scoop them up whenever they drift into view.",
            },
            {
                "icon": "\u26A0",
                "accent": "#D69A55",
                "title": "Don't Drop or Switch Hands",
                "desc": "Dropping a star before delivery, or grabbing with the wrong hand, won't count \u2014 steady and careful wins.",
            },
        ],
        "footer_title": "Constellation Growing!",
        "footer_desc": "Every star you deliver lights up part of your night sky \u2014 keep weaving.",
    },
}


class InstructionsPage(QWidget):

    play_confirmed = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._game_id = None
        self._steps = []
        self._current_index = 0
        self._dots = []
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 28, 36, 20)
        outer.setSpacing(4)

        header_row = QHBoxLayout()
        back_btn = QPushButton("\u2039  Back to Games")
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
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)
        header_row.addStretch()
        outer.addLayout(header_row)
        outer.addSpacing(2)

        self.heading_label = QLabel()
        heading_font = QFont("Segoe UI", 19)
        heading_font.setWeight(QFont.Weight.DemiBold)
        self.heading_label.setFont(heading_font)
        self.heading_label.setStyleSheet("color: #2E2350; background: transparent;")
        outer.addWidget(self.heading_label)

        self.subheading_label = QLabel()
        self.subheading_label.setStyleSheet("color: rgba(45, 35, 80, 160); background: transparent; font-size: 12px;")
        outer.addWidget(self.subheading_label)
        outer.addSpacing(10)

        # ---- steps area: carousel + dots, wrapped in one widget so it
        # can be hidden as a unit if a game has no steps defined yet ----
        self.steps_widget = QWidget()
        steps_outer = QVBoxLayout(self.steps_widget)
        steps_outer.setContentsMargins(0, 0, 0, 0)
        steps_outer.setSpacing(10)

        carousel_row = QHBoxLayout()
        carousel_row.setSpacing(14)

        self.prev_btn = self._make_arrow_button("\u2039")
        self.prev_btn.clicked.connect(self._go_prev)
        carousel_row.addWidget(self.prev_btn)

        self.step_card = QFrame()
        self.step_card.setFixedHeight(240)
        self.step_card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 225);
                border-radius: 20px;
            }
        """)
        card_layout = QVBoxLayout(self.step_card)
        card_layout.setContentsMargins(28, 20, 28, 20)
        card_layout.setSpacing(6)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.step_kicker = QLabel()
        kicker_font = QFont("Segoe UI", 9)
        kicker_font.setWeight(QFont.Weight.DemiBold)
        kicker_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        self.step_kicker.setFont(kicker_font)
        self.step_kicker.setStyleSheet("color: #A79BC7; background: transparent;")
        self.step_kicker.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(self.step_kicker)

        self.step_badge = QLabel()
        self.step_badge.setFixedSize(76, 76)
        self.step_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_font = QFont("Segoe UI", 34)
        self.step_badge.setFont(badge_font)
        card_layout.addWidget(self.step_badge, 0, Qt.AlignmentFlag.AlignHCenter)

        self.step_title = QLabel()
        title_font = QFont("Segoe UI", 16)
        title_font.setWeight(QFont.Weight.DemiBold)
        self.step_title.setFont(title_font)
        self.step_title.setStyleSheet("color: #2E2350; background: transparent;")
        self.step_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(self.step_title)

        self.step_desc = QLabel()
        self.step_desc.setWordWrap(True)
        self.step_desc.setStyleSheet("color: #6B5C93; background: transparent; font-size: 12px;")
        self.step_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.step_desc.setFixedWidth(420)
        card_layout.addWidget(self.step_desc, 0, Qt.AlignmentFlag.AlignHCenter)

        carousel_row.addWidget(self.step_card, 1)

        self.next_btn = self._make_arrow_button("\u203A")
        self.next_btn.clicked.connect(self._go_next)
        carousel_row.addWidget(self.next_btn)

        steps_outer.addLayout(carousel_row)
        steps_outer.addSpacing(10)

        # ---- dot progress indicator ----
        self.dots_row = QHBoxLayout()
        self.dots_row.setSpacing(8)
        self.dots_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        steps_outer.addLayout(self.dots_row)

        outer.addWidget(self.steps_widget)
        outer.addSpacing(14)

        # ---- footer: round complete summary (not a numbered step) ----
        self.footer_frame = QFrame()
        self.footer_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(111, 191, 143, 45);
                border: 1px solid rgba(111, 191, 143, 120);
                border-radius: 14px;
            }
        """)
        footer_layout = QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        footer_layout.setSpacing(12)

        footer_icon = QLabel("\u2705")
        footer_icon.setStyleSheet("background: transparent; font-size: 18px;")
        footer_layout.addWidget(footer_icon)

        footer_text_col = QVBoxLayout()
        footer_text_col.setSpacing(0)
        self.footer_title_label = QLabel()
        footer_title_font = QFont("Segoe UI", 11)
        footer_title_font.setWeight(QFont.Weight.DemiBold)
        self.footer_title_label.setFont(footer_title_font)
        self.footer_title_label.setStyleSheet("color: #2E2350; background: transparent;")
        footer_text_col.addWidget(self.footer_title_label)
        self.footer_desc_label = QLabel()
        self.footer_desc_label.setStyleSheet("color: #4C6B58; background: transparent; font-size: 10px;")
        self.footer_desc_label.setWordWrap(True)
        footer_text_col.addWidget(self.footer_desc_label)
        footer_layout.addLayout(footer_text_col, 1)

        outer.addWidget(self.footer_frame)
        outer.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        play_btn = QPushButton("Let's Begin  \u25B6")
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setFixedSize(200, 42)
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
        play_btn.clicked.connect(lambda: self.play_confirmed.emit(self._game_id))
        bottom_row.addWidget(play_btn)
        outer.addLayout(bottom_row)

    def _make_arrow_button(self, symbol):
        btn = QPushButton(symbol)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(40, 40)
        arrow_font = QFont("Segoe UI", 16)
        arrow_font.setWeight(QFont.Weight.Bold)
        btn.setFont(arrow_font)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 20px;
                color: #7C5CE0;
            }
            QPushButton:hover {
                background-color: #7C5CE0;
                color: white;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 90);
                color: rgba(124, 92, 224, 90);
            }
        """)
        return btn

    # ------------------------------------------------------------------
    def load(self, game_id):
        self._game_id = game_id
        content = GAME_INSTRUCTIONS.get(game_id, {})

        self.heading_label.setText(content.get("title", "How to Play"))
        self.footer_title_label.setText(content.get("footer_title", "Round Complete!"))
        self.footer_desc_label.setText(content.get("footer_desc", ""))

        self._steps = content.get("steps", [])
        self._current_index = 0
        self.subheading_label.setText(content.get("subtitle", ""))

        if not self._steps:
            # no step-by-step guide written for this game yet
            self.steps_widget.hide()
            self.footer_frame.hide()
            return

        self.steps_widget.show()
        self.footer_frame.show()

        # rebuild the dot indicators for however many steps this game has
        while self.dots_row.count():
            item = self.dots_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._dots = []
        for _ in self._steps:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            self._dots.append(dot)
            self.dots_row.addWidget(dot)

        self._render_step()

    def _go_prev(self):
        if self._current_index > 0:
            self._current_index -= 1
            self._render_step()

    def _go_next(self):
        if self._current_index < len(self._steps) - 1:
            self._current_index += 1
            self._render_step()

    def _render_step(self):
        if not self._steps:
            self.step_kicker.setText("")
            self.step_badge.setText("\u2728")
            self.step_badge.setStyleSheet("""
                background-color: #E4D6F5;
                border-radius: 38px;
            """)
            self.step_title.setText("Instructions coming soon")
            self.step_desc.setText("This game's step-by-step guide isn't ready yet - check back shortly.")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        step = self._steps[self._current_index]
        total = len(self._steps)

        self.step_kicker.setText(f"STEP {self._current_index + 1} OF {total}")
        self.step_badge.setText(step["icon"])
        self.step_badge.setStyleSheet(f"""
            background-color: {step['accent']};
            border-radius: 38px;
        """)
        self.step_title.setText(step["title"])
        self.step_desc.setText(step["desc"])

        for i, dot in enumerate(self._dots):
            if i == self._current_index:
                dot.setStyleSheet("background-color: #7C5CE0; border-radius: 4px;")
            else:
                dot.setStyleSheet("background-color: rgba(124, 92, 224, 60); border-radius: 4px;")

        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < total - 1)