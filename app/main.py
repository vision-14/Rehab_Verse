"""
RehabVerse - App Shell
------------------------
One persistent, frameless, rounded window for the whole app. The splash
screen and login screen are pages inside a QStackedWidget, so moving from
splash -> login is a soft crossfade *inside* the same window - nothing
closes, nothing reopens, no window flicker on Windows.

Run this file to launch the app: python main.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QStackedWidget, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QPainterPath, QRegion

from splash_screen import SplashScreen
from login_page import LoginPage
from dashboard_page import DashboardPage
from game_launcher import launch_game


WINDOW_W, WINDOW_H = 900, 560
CORNER_RADIUS = 26


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RehabVerse")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(WINDOW_W, WINDOW_H)
        self._center_on_screen()
        self._apply_rounded_mask()
        self.current_user_id = None

        # ---- pages ----
        self.stack = QStackedWidget(self)
        self.stack.setGeometry(0, 0, WINDOW_W, WINDOW_H)

        self.splash_page = SplashScreen(self.stack)
        self.login_page = LoginPage(self.stack)
        self.dashboard_page = DashboardPage(self.stack)
        self.stack.addWidget(self.splash_page)
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard_page)
        self.stack.setCurrentWidget(self.splash_page)

        # ---- custom close button (frameless window needs its own) ----
        self.close_btn = QPushButton("\u2715", self)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 18);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 15px;
                color: #D2CDEB;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 120, 140, 60);
                color: #FFFFFF;
            }
        """)
        self.close_btn.move(WINDOW_W - 44, 14)
        self.close_btn.raise_()
        self.close_btn.clicked.connect(self.close)

        # ---- wire up navigation ----
        self.splash_page.finished.connect(self.show_login)
        self.login_page.login_requested.connect(self._on_login_requested)
        self.dashboard_page.game_selected.connect(self._on_game_selected)

        # ---- initial window fade-in ----
        self.setWindowOpacity(0.0)
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(700)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ------------------------------------------------------------------
    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _apply_rounded_mask(self):
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), CORNER_RADIUS, CORNER_RADIUS)
        polygon = path.toFillPolygon().toPolygon()
        self.setMask(QRegion(polygon))

    def start(self, splash_hold_ms=2600):
        self.show()
        self.fade_in.start()
        self.splash_page.run(splash_hold_ms)

    # ------------------------------------------------------------------
    def show_login(self):
        """Crossfade from whatever page is showing to the login page."""
        self._crossfade_to(self.login_page)

    def show_splash(self):
        self._crossfade_to(self.splash_page)

    def _crossfade_to(self, target_page):
        current_page = self.stack.currentWidget()
        if current_page is target_page:
            return

        fade_out_effect = QGraphicsOpacityEffect(current_page)
        current_page.setGraphicsEffect(fade_out_effect)
        fade_out = QPropertyAnimation(fade_out_effect, b"opacity", self)
        fade_out.setDuration(380)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _switch():
            current_page.setGraphicsEffect(None)
            self.stack.setCurrentWidget(target_page)

            fade_in_effect = QGraphicsOpacityEffect(target_page)
            target_page.setGraphicsEffect(fade_in_effect)
            fade_in = QPropertyAnimation(fade_in_effect, b"opacity", self)
            fade_in.setDuration(420)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_in.finished.connect(lambda: target_page.setGraphicsEffect(None))
            self._active_fade_in = fade_in  # keep a reference alive
            fade_in.start()

        fade_out.finished.connect(_switch)
        self._active_fade_out = fade_out  # keep a reference alive
        fade_out.start()

    # ------------------------------------------------------------------
    def _on_login_requested(self, user_id, name):
        # LoginPage has already authenticated (or freshly registered) this
        # user against MongoDB via auth.py by the time this fires.
        print(f"[RehabVerse] Signed in -> user_id={user_id} name={name}")
        self.current_user_id = user_id
        self.dashboard_page.set_user_id(user_id)
        self.dashboard_page.set_user_name(name)
        self.dashboard_page.sidebar.set_active("home")
        self.dashboard_page.content_stack.setCurrentWidget(self.dashboard_page.home_view)
        self.show_dashboard()

    def show_dashboard(self):
        self._crossfade_to(self.dashboard_page)

    def _on_game_selected(self, game_id, hand_pref):
        print(f"[RehabVerse] Start game requested -> {game_id} "
              f"(user={self.current_user_id}, hand_pref={hand_pref!r})")
        launch_game(game_id, user_id=self.current_user_id, hand_pref=hand_pref,
                    on_finished=self._on_game_finished)
        # NOTE: launch_game currently prints if the Unity build / Python
        # script aren't found yet, rather than raising - that's expected
        # until the real files are in place at the paths in game_launcher.py.

    def _on_game_finished(self, game_id, user_id, exit_code):
        print(f"[RehabVerse] Game finished -> {game_id} (exit_code={exit_code})")
        # The Python controller already saved the session to Mongo before
        # exiting (and game_launcher.py has already closed the matching
        # Unity window and brought this app back to the front).
        self.show_dashboard()

        # Simplified: every game goes straight to the Report tab, no
        # per-game special case. (Previously cosmic_weaver ran a
        # background Mongo lookup - _StarProgressWorker - then showed a
        # constellation star-reveal animation before landing on Report;
        # that whole path has been removed, along with the worker class
        # and show_star_reveal_for_game(), per request.)
        self.dashboard_page.show_report_for_game(game_id)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.start(splash_hold_ms=2600)
    sys.exit(app.exec())