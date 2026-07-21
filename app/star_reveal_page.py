"""
Star Reveal Page
------------------
Shown right after a Cosmic Weaver session ends, before the Report tab.
Animates the constellation scene filling in star-by-star from wherever
the player's cumulative total stood before this session, up through
however many points they just scored - so the player visually SEES their
new stars join the ones already lit from past sessions, instead of the
scene just silently jumping to the new total.

After the fill animation finishes, holds for a few seconds so the player
can take in the result, then emits finished(game_id) so the dashboard can
move on to the Report tab.

Only used for cosmic_weaver - see dashboard_page.py for where this gets
skipped for games without a constellation scene.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from cosmic_background import CosmicPage
from cosmic_weaver_scene import CosmicWeaverScene

STAR_STEP_MS = 250      # delay between each newly-lit star
HOLD_AFTER_MS = 3000    # pause once the fill finishes, before moving on


class StarRevealPage(CosmicPage):
    """Uses CosmicPage (the same dark starry background as login/hand-
    preference) instead of plain QWidget - without it, this page inherited
    the dashboard's light bloom background, and the light-colored caption
    text was unreadable against it (only the scene widget itself was dark,
    not the page around it)."""

    finished = pyqtSignal(str)  # game_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._game_id = None
        self._target_count = 0
        self._current_count = 0

        self._fill_timer = QTimer(self)
        self._fill_timer.timeout.connect(self._tick)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.caption = QLabel()
        caption_font = QFont("Segoe UI", 15)
        caption_font.setWeight(QFont.Weight.DemiBold)
        self.caption.setFont(caption_font)
        self.caption.setStyleSheet("color: #F1EEFB; background: transparent;")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.caption)

        self.scene = CosmicWeaverScene()
        layout.addWidget(self.scene, 1)

    # ------------------------------------------------------------------
    def load(self, game_id, previous_total, session_gain):
        """Starts the reveal: begins lit at previous_total, animates up
        to previous_total + session_gain (clamped to the scene's actual
        star count), then holds and emits finished(game_id)."""
        self._game_id = game_id
        self._current_count = previous_total
        self._target_count = min(
            previous_total + session_gain, self.scene.total_star_count()
        )

        self.scene.set_lit_stars(self._current_count)
        star_word = "star" if session_gain == 1 else "stars"
        self.caption.setText(f"+{session_gain} {star_word} this session \u2728")

        self._fill_timer.stop()
        if self._current_count < self._target_count:
            self._fill_timer.start(STAR_STEP_MS)
        else:
            # nothing new to animate (e.g. session_gain was 0) - just hold
            # for the same duration a normal fill would, then move on
            QTimer.singleShot(HOLD_AFTER_MS, self._finish)

    def _tick(self):
        self._current_count += 1
        self.scene.set_lit_stars(self._current_count)
        if self._current_count >= self._target_count:
            self._fill_timer.stop()
            QTimer.singleShot(HOLD_AFTER_MS, self._finish)

    def _finish(self):
        self.finished.emit(self._game_id)