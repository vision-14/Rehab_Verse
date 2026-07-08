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
from session_data import get_current_streak


class DashboardPage(BloomPage):

    game_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_fade_out = None
        self._active_fade_in = None
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
        self.games_view.game_selected.connect(self.game_selected.emit)
        self.home_view.play_requested.connect(self._go_to_games)

        self.content_stack.addWidget(self.home_view)
        self.content_stack.addWidget(self.games_view)
        self.content_stack.addWidget(self.progress_view)
        self.content_stack.setCurrentWidget(self.home_view)

        layout.addWidget(self.content_stack, 1)

        self.sidebar.set_streak(get_current_streak())

    # ------------------------------------------------------------------
    def set_user_name(self, name):
        self.sidebar.set_user_name(name)
        self.home_view.set_user_name(name)

    def _on_nav_changed(self, key):
        target = {
            "home": self.home_view,
            "games": self.games_view,
            "progress": self.progress_view,
        }.get(key)
        if target is not None:
            self._crossfade_to(target)

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
    win.game_selected.connect(lambda gid: print(f"Start game: {gid}"))
    win.show()
    sys.exit(app.exec())