"""
Rehab Verse - Login Screen (Cosmic / Bloom theme)
---------------------------------------------------
Same animated cosmic background as the splash screen. Authenticates
against the real MongoDB `users` collection via auth.py (which mirrors
the game backend's login()/auto-register logic exactly, just without
blocking on input()).

NOTE: the backend's `users` collection has no email field - accounts are
identified by a generated User ID (e.g. "IPS1234"), not Gmail. So this
screen asks for User ID + Password, with an inline toggle to create an
account (matching the backend's "create one if it doesn't exist" flow),
instead of a Gmail-specific field.

The actual Mongo call runs on a background QThread (_AuthWorker) so a
slow/dropped Atlas connection never freezes the window's animations or
the crossfade - the submit button just shows a busy state until it
resolves.

Emits:
    login_requested(user_id: str, name: str)
        -> fired only after a real login or a fresh registration succeeds
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from cosmic_background import CosmicPage
from auth import login as db_login, register as db_register, AuthError


class _AuthWorker(QThread):
    """Runs a single login or register call against MongoDB off the UI
    thread. status is one of: "ok", "no_such_user", "wrong_password",
    "user_exists", "error" (network/Mongo issue)."""

    result_ready = pyqtSignal(str, object)

    def __init__(self, mode, user_id, password, name=None):
        super().__init__()
        self.mode = mode
        self.user_id = user_id
        self.password = password
        self.name = name

    def run(self):
        try:
            if self.mode == "register":
                user = db_register(self.user_id, self.name, self.password)
            else:
                user = db_login(self.user_id, self.password)
            self.result_ready.emit("ok", user)
        except AuthError as e:
            self.result_ready.emit(e.reason, None)
        except Exception as exc:
            print(f"[RehabVerse] Mongo auth error: {exc}")
            self.result_ready.emit("error", None)


class LoginPage(CosmicPage):

    login_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "login"  # or "register"
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(self)
        card.setObjectName("loginCard")
        card.setFixedWidth(380)
        card.setStyleSheet("""
            QFrame#loginCard {
                background-color: rgba(255, 255, 255, 18);
                border: 1px solid rgba(200, 190, 255, 55);
                border-radius: 22px;
            }
        """)
        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 34, 36, 30)
        card_layout.setSpacing(4)

        # ---- brand mark ----
        brand = QLabel("REHABVERSE")
        brand_font = QFont("Segoe UI", 11)
        brand_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        brand_font.setWeight(QFont.Weight.DemiBold)
        brand.setFont(brand_font)
        brand.setStyleSheet("color: #B8A3EF; background: transparent;")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(brand)
        card_layout.addSpacing(14)

        # ---- heading (text swaps between login / register) ----
        self.heading_label = QLabel()
        heading_font = QFont("Segoe UI", 22)
        heading_font.setWeight(QFont.Weight.Light)
        self.heading_label.setFont(heading_font)
        self.heading_label.setStyleSheet("color: #F1EEFB; background: transparent;")
        self.heading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.heading_label)

        self.subheading_label = QLabel()
        self.subheading_label.setStyleSheet("color: rgba(210, 205, 235, 170); background: transparent;")
        self.subheading_label.setFont(QFont("Segoe UI", 10))
        self.subheading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.subheading_label)
        card_layout.addSpacing(22)

        field_style = """
            QLineEdit {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 10px;
                padding: 10px 12px;
                color: #F1EEFB;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #B8A3EF;
                background-color: rgba(255, 255, 255, 24);
            }
        """
        label_style = "color: #C9BFF2; background: transparent;"
        label_font = QFont("Segoe UI", 9)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        label_font.setWeight(QFont.Weight.DemiBold)

        # ---- name field (register mode only) ----
        self.name_label = QLabel("NAME")
        self.name_label.setFont(label_font)
        self.name_label.setStyleSheet(label_style)
        card_layout.addWidget(self.name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your full name")
        self.name_input.setStyleSheet(field_style)
        self.name_input.textChanged.connect(self._clear_error)
        card_layout.addWidget(self.name_input)
        card_layout.addSpacing(14)

        # ---- user id field ----
        user_id_label = QLabel("USER ID")
        user_id_label.setFont(label_font)
        user_id_label.setStyleSheet(label_style)
        card_layout.addWidget(user_id_label)

        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("e.g. IPS1234")
        self.user_id_input.setStyleSheet(field_style)
        self.user_id_input.textChanged.connect(self._clear_error)
        card_layout.addWidget(self.user_id_input)
        card_layout.addSpacing(14)

        # ---- password field ----
        pw_row = QHBoxLayout()
        pw_label = QLabel("PASSWORD")
        pw_label.setFont(label_font)
        pw_label.setStyleSheet(label_style)
        pw_row.addWidget(pw_label)
        pw_row.addStretch()
        self.forgot_link = QLabel('<a href="#" style="color:#8FE3E0; text-decoration:none;">Forgot password?</a>')
        self.forgot_link.setFont(QFont("Segoe UI", 9))
        self.forgot_link.setStyleSheet("background: transparent;")
        self.forgot_link.setOpenExternalLinks(False)
        pw_row.addWidget(self.forgot_link)
        card_layout.addLayout(pw_row)

        pw_field_row = QHBoxLayout()
        pw_field_row.setSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(field_style)
        self.password_input.textChanged.connect(self._clear_error)
        pw_field_row.addWidget(self.password_input)

        self.toggle_pw_btn = QPushButton("Show")
        self.toggle_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pw_btn.setFixedWidth(52)
        self.toggle_pw_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 10px;
                color: #C9BFF2;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 26); }
        """)
        self.toggle_pw_btn.clicked.connect(self._toggle_password_visibility)
        pw_field_row.addWidget(self.toggle_pw_btn)
        card_layout.addLayout(pw_field_row)
        card_layout.addSpacing(10)

        # ---- remember me ----
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox { color: rgba(210, 205, 235, 190); background: transparent; font-size: 12px; }
            QCheckBox::indicator {
                width: 15px; height: 15px; border-radius: 4px;
                border: 1px solid rgba(255,255,255,60);
                background-color: rgba(255,255,255,10);
            }
            QCheckBox::indicator:checked {
                background-color: #B8A3EF;
                border: 1px solid #B8A3EF;
            }
        """)
        card_layout.addWidget(self.remember_checkbox)
        card_layout.addSpacing(8)

        # ---- error label ----
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F2A6C2; background: transparent; font-size: 11px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        # ---- submit button (text swaps between login / register) ----
        self.submit_btn = QPushButton()
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.setFixedHeight(42)
        self.submit_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6FC8C4, stop:0.5 #967FD8, stop:1 #C77FD0
                );
            }
        """)
        self.submit_btn.clicked.connect(self._handle_submit)
        card_layout.addWidget(self.submit_btn)
        card_layout.addSpacing(16)

        # ---- mode toggle link ----
        self.toggle_mode_label = QLabel()
        self.toggle_mode_label.setStyleSheet("color: rgba(210, 205, 235, 170); background: transparent;")
        self.toggle_mode_label.setFont(QFont("Segoe UI", 10))
        self.toggle_mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toggle_mode_label.setOpenExternalLinks(False)
        self.toggle_mode_label.linkActivated.connect(lambda _: self._toggle_mode())
        card_layout.addWidget(self.toggle_mode_label)

        self.user_id_input.returnPressed.connect(self._handle_submit)
        self.password_input.returnPressed.connect(self._handle_submit)
        self.name_input.returnPressed.connect(self._handle_submit)

        self._apply_mode()

    # ------------------------------------------------------------------
    def _toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pw_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pw_btn.setText("Show")

    def _clear_error(self):
        self.error_label.hide()
        self.error_label.setText("")

    def _show_error(self, text):
        self.error_label.setText(text)
        self.error_label.show()

    def _toggle_mode(self):
        self._mode = "register" if self._mode == "login" else "login"
        self._clear_error()
        self._apply_mode()

    def _apply_mode(self):
        is_register = (self._mode == "register")
        self.name_label.setVisible(is_register)
        self.name_input.setVisible(is_register)

        if is_register:
            self.heading_label.setText("Create Account \u2728")
            self.subheading_label.setText("Set up your RehabVerse profile")
            self.submit_btn.setText("Create Account")
            self.forgot_link.setVisible(False)
            self.remember_checkbox.setVisible(False)
            self.toggle_mode_label.setText(
                'Already have an account? '
                '<a href="#" style="color:#8FE3E0; text-decoration:none;">Log in</a>'
            )
        else:
            self.heading_label.setText("Welcome Back \U0001F338")
            self.subheading_label.setText("Sign in to continue your journey")
            self.submit_btn.setText("Sign In  \u2728")
            self.forgot_link.setVisible(True)
            self.remember_checkbox.setVisible(True)
            self.toggle_mode_label.setText(
                'New here? '
                '<a href="#" style="color:#E3A6E8; text-decoration:none;">Create an account</a>'
            )

    def _handle_submit(self):
        user_id = self.user_id_input.text().strip()
        password = self.password_input.text()

        if not user_id:
            self._show_error("Please enter your User ID.")
            return
        if not password:
            self._show_error("Please enter your password.")
            return

        name = None
        if self._mode == "register":
            name = self.name_input.text().strip()
            if not name:
                self._show_error("Please enter your name.")
                return

        self._clear_error()
        self.set_busy(True)

        # Keep a reference on self so the thread isn't garbage-collected
        # mid-flight - PyQt doesn't keep it alive on its own.
        self._auth_worker = _AuthWorker(self._mode, user_id, password, name)
        self._auth_worker.result_ready.connect(self._handle_auth_result)
        self._auth_worker.start()

    def _handle_auth_result(self, status, user):
        self.set_busy(False)

        if status == "ok":
            self.login_requested.emit(user["user_id"], user["name"])
        elif status == "no_such_user":
            self._show_error("No account with that User ID. Use \u201cCreate an account\u201d below.")
        elif status == "wrong_password":
            self._show_error("Incorrect password.")
        elif status == "user_exists":
            self._show_error("That User ID is already taken - try logging in instead.")
        else:  # "error" - network/Mongo issue
            self._show_error("Couldn't reach the database. Please try again in a moment.")

    def set_busy(self, is_busy):
        """Disables the form and shows a busy label on the button while a
        Mongo call is in flight."""
        self.submit_btn.setEnabled(not is_busy)
        self.user_id_input.setEnabled(not is_busy)
        self.password_input.setEnabled(not is_busy)
        self.name_input.setEnabled(not is_busy)
        self.toggle_pw_btn.setEnabled(not is_busy)
        self.toggle_mode_label.setEnabled(not is_busy)

        if is_busy:
            self.submit_btn.setText(
                "Signing in\u2026" if self._mode == "login" else "Creating account\u2026"
            )
        else:
            self._apply_mode()  # restores the correct label/text for the current mode

    def reset_fields(self):
        self.name_input.clear()
        self.user_id_input.clear()
        self.password_input.clear()
        self.remember_checkbox.setChecked(False)
        self._clear_error()


# ----------------------------------------------------------------------
# Standalone preview: `python login_page.py`
# ----------------------------------------------------------------------
class _PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(900, 560)
        self.login = LoginPage(self)
        self.login.setGeometry(0, 0, 900, 560)
        self.login.login_requested.connect(
            lambda user_id, name: print(f"Login requested: {user_id} ({name})")
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = _PreviewWindow()
    win.show()
    sys.exit(app.exec())