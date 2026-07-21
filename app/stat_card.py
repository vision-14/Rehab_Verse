"""
Stat Card
-----------
The small rounded "big number + label" card used across the dashboard
(Progress tab, Report tab). Pulled into its own module so every screen
shares the exact same look instead of each defining their own copy.

Set clickable=True to get a card that reacts to hover and emits a
`clicked` signal - used e.g. by the Progress tab's session-count cards,
which open a graphical breakdown when clicked.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class StatCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, clickable=False, parent=None):
        super().__init__(parent)
        self._clickable = clickable
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


def make_stat_card(value_text, label_text, accent="#7C5CE0", clickable=False):
    """Returns (card_widget, value_label) - keep the value_label reference
    if you'll need to update the number later. If clickable=True, connect
    to card_widget.clicked to react to taps."""
    card = StatCard(clickable=clickable)
    card.setFixedHeight(88)
    hover_extra = "QFrame:hover { background-color: rgba(255, 255, 255, 255); }" if clickable else ""
    card.setStyleSheet(f"""
        QFrame {{
            background-color: rgba(255, 255, 255, 225);
            border-radius: 16px;
        }}
        {hover_extra}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(2)

    value = QLabel(value_text)
    value_font = QFont("Segoe UI", 22)
    value_font.setWeight(QFont.Weight.Bold)
    value.setFont(value_font)
    value.setStyleSheet(f"color: {accent}; background: transparent;")
    layout.addWidget(value)

    label_row_text = label_text + ("  \u203A" if clickable else "")
    label = QLabel(label_row_text)
    label.setStyleSheet("color: #8A7CB0; background: transparent; font-size: 11px;")
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch()

    return card, value