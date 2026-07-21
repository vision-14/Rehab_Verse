"""
Night Sky View
----------------
Full-screen, static view of the Cosmic Weaver constellation scene at the
player's current cumulative star total (total score // 4) - just the sky,
no cards, no charts. Lives inside the Progress tab's own view stack,
reached via the "Night Sky" card on the Progress overview page.

Call load(user_id) right before switching to this page so it always
shows the current total, not whatever was loaded last time it was open.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from cosmic_weaver_scene import CosmicWeaverScene
from session_data import get_cosmic_weaver_star_count


class NightSkyView(QWidget):

    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 20)
        layout.setSpacing(8)

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
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn)

        heading = QLabel("Your Night Sky")
        heading_font = QFont("Segoe UI", 19)
        heading_font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #2E2350; background: transparent;")
        layout.addWidget(heading)

        self.subheading = QLabel()
        self.subheading.setStyleSheet("color: rgba(45, 35, 80, 160); background: transparent; font-size: 12px;")
        layout.addWidget(self.subheading)
        layout.addSpacing(6)

        # fills the rest of the available space - genuinely full-screen
        # within the content area, not a small banner like the
        # instructions page's version
        self.scene = CosmicWeaverScene()
        layout.addWidget(self.scene, 1)

    # ------------------------------------------------------------------
    def load(self, user_id):
        star_count = get_cosmic_weaver_star_count(user_id) if user_id else 0
        total = self.scene.total_star_count()
        self.scene.set_lit_stars(star_count)
        self.subheading.setText(
            f"{star_count} of {total} stars lit \u2014 keep playing Cosmic Weaver to fill the sky."
        )