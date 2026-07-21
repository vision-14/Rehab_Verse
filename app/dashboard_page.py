"""
Dashboard Page
----------------
The screen that appears after a successful sign-in. Combines the light
bloom background, the persistent sidebar, and a content area that
crossfades between Home, Games, and Progress as the user clicks around -
all inside this one page (which itself lives inside main.py's window).
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont

from bloom_background import BloomPage
from sidebar import Sidebar
from home_view import HomeView
from games_view import GamesView
from progress_view import ProgressView
from game_report_view import GameReportView
from instructions_page import InstructionsPage
from hand_preference_page import HandPreferencePage
from star_reveal_page import StarRevealPage
from session_data import get_current_streak


class DashboardPage(BloomPage):

    game_selected = pyqtSignal(str, str)  # (game_id, hand_pref) - hand_pref is "" when not applicable

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_fade_out = None
        self._active_fade_in = None
        self.current_user_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        self.sidebar = Sidebar(self)
        self.sidebar.nav_changed.connect(self._on_nav_changed)
        layout.addWidget(self.sidebar)

        self.content_stack = QStackedWidget(self)
        self.content_stack.setStyleSheet("background: transparent;")

        self.home_view = HomeView()
        self.games_view = GamesView()
        self.progress_view = ProgressView()
        self.report_view = GameReportView()
        self.instructions_page = InstructionsPage()
        self.hand_preference_page = HandPreferencePage()
        self.star_reveal_page = StarRevealPage()

        # Start Game no longer launches immediately - it shows how-to-play
        # instructions first. The instructions page's own "Let's Play!"
        # button either goes to hand-preference (Cosmic Weaver) or
        # launches directly (any game that doesn't need that step).
        self.games_view.game_selected.connect(self._show_instructions_for_game)
        self.instructions_page.play_confirmed.connect(self._on_play_confirmed)
        self.instructions_page.back_requested.connect(self._go_to_games)
        self.hand_preference_page.confirmed.connect(self._on_hand_preference_confirmed)
        self.hand_preference_page.back_requested.connect(
            lambda: self._crossfade_to(self.instructions_page)
        )
        self.home_view.play_requested.connect(self._go_to_games)

        # Star reveal animation (cosmic_weaver only) always lands on the
        # Report tab once it finishes - see show_star_reveal_for_game().
        self.star_reveal_page.finished.connect(self.show_report_for_game)

        self.content_stack.addWidget(self.home_view)
        self.content_stack.addWidget(self.games_view)
        self.content_stack.addWidget(self.progress_view)
        self.content_stack.addWidget(self.report_view)
        self.content_stack.addWidget(self.instructions_page)
        self.content_stack.addWidget(self.hand_preference_page)
        self.content_stack.addWidget(self.star_reveal_page)
        self.content_stack.setCurrentWidget(self.home_view)

        layout.addWidget(self.content_stack, 1)

    # ------------------------------------------------------------------
    def set_user_name(self, name):
        self.sidebar.set_user_name(name)
        self.home_view.set_user_name(name)

    def set_user_id(self, user_id):
        """Call this once at login - refreshes every tab's real data for
        this specific user (streak, weekly activity, session counts)."""
        self.current_user_id = user_id
        self.sidebar.set_streak(get_current_streak(user_id))
        self.home_view.refresh_for_user(user_id)
        self.progress_view.refresh_for_user(user_id)

    def _on_nav_changed(self, key):
        target = {
            "home": self.home_view,
            "games": self.games_view,
            "progress": self.progress_view,
            "report": self.report_view,
        }.get(key)
        if target is not None:
            # Refresh whichever data-driven tab is being opened, so it's
            # never showing stale numbers from earlier in the session
            # (e.g. right after finishing a game).
            if target is self.report_view:
                self.report_view.load(self.current_user_id)
            elif target is self.home_view:
                self.home_view.refresh_for_user(self.current_user_id)
            elif target is self.progress_view:
                self.progress_view.refresh_for_user(self.current_user_id)
            self._crossfade_to(target)

    def show_report_for_game(self, game_id):
        """Called by main.py the moment a game process exits (directly for
        most games, or via star_reveal_page.finished for cosmic_weaver) -
        jumps the dashboard straight to the Report tab with that game's
        just-saved session already loaded, and refreshes the streak/Home/
        Progress data in the background since a new session just landed."""
        self.report_view.load(self.current_user_id, game_id)
        self.sidebar.set_active("report")
        self._crossfade_to(self.report_view)

        self.sidebar.set_streak(get_current_streak(self.current_user_id))
        self.home_view.refresh_for_user(self.current_user_id)
        self.progress_view.refresh_for_user(self.current_user_id)

    def show_star_reveal_for_game(self, game_id, previous_total, session_gain):
        """Called by main.py instead of show_report_for_game() when
        game_id == 'cosmic_weaver' - shows the constellation fill
        animation first; the Report tab is shown automatically once that
        finishes (see star_reveal_page.finished connection above)."""
        self.star_reveal_page.load(game_id, previous_total, session_gain)
        self._crossfade_to(self.star_reveal_page)

    def _show_instructions_for_game(self, game_id):
        self.instructions_page.load(game_id)
        self._crossfade_to(self.instructions_page)

    # games that need a hand-preference choice before launching
    GAMES_NEEDING_HAND_PREFERENCE = {"cosmic_weaver"}

    def _on_play_confirmed(self, game_id):
        if game_id in self.GAMES_NEEDING_HAND_PREFERENCE:
            self.hand_preference_page.load(game_id)
            self._crossfade_to(self.hand_preference_page)
        else:
            self.game_selected.emit(game_id, "")  # bubbles up to main.py, which launches it
            self._go_to_games()

    def _on_hand_preference_confirmed(self, game_id, hand_pref):
        self.game_selected.emit(game_id, hand_pref)  # bubbles up to main.py, which launches it
        self._go_to_games()  # land back on Games while Unity/Python open separately

    def _go_to_games(self):
        self.sidebar.set_active("games")
        self._crossfade_to(self.games_view)

    def _crossfade_to(self, target_widget):
        current = self.content_stack.currentWidget()
        if current is target_widget:
            return

        fade_out_effect = QGraphicsOpacityEffect(current)
        current.setGraphicsEffect(fade_out_effect)
        fade_out = QPropertyAnimation(fade_out_effect, b"opacity", self)
        fade_out.setDuration(220)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _switch():
            current.setGraphicsEffect(None)
            self.content_stack.setCurrentWidget(target_widget)

            fade_in_effect = QGraphicsOpacityEffect(target_widget)
            target_widget.setGraphicsEffect(fade_in_effect)
            fade_in = QPropertyAnimation(fade_in_effect, b"opacity", self)
            fade_in.setDuration(260)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_in.finished.connect(lambda: target_widget.setGraphicsEffect(None))
            self._active_fade_in = fade_in
            fade_in.start()

        fade_out.finished.connect(_switch)
        self._active_fade_out = fade_out
        fade_out.start()


# ----------------------------------------------------------------------
# Standalone preview: `python dashboard_page.py`
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = DashboardPage()
    win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    win.setFixedSize(900, 560)
    win.set_user_name("Ipsita")
    win.set_user_id("IPS1234")  # swap for a real test user_id in your DB to see live data
    win.game_selected.connect(lambda gid, hand: print(f"Start game: {gid} (hand={hand!r})"))
    win.show()
    sys.exit(app.exec())