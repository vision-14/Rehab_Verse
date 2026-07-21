"""
Cosmic Weaver Pager
----------------------
Wraps two CosmicWeaverScene pages (see cosmic_weaver_scene.py) and
handles sliding from the first to the second once Page 1's stars are all
lit - a real horizontal slide/scroll transition, not a fade.

Call set_lit_stars(n) with a running total across BOTH pages combined -
same calling convention CosmicWeaverScene itself uses, just spanning a
bigger combined total now:
  - n <= Page 1's star count  -> shows Page 1, lit up to n
  - n >  Page 1's star count  -> Page 1 shown fully lit, auto-slides to
    Page 2, and Page 2 lights up (n - page_1_total) stars

total_star_count() returns the combined capacity across both pages.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect

from cosmic_weaver_scene import CosmicWeaverScene, PAGE_1_CONSTELLATIONS, PAGE_2_CONSTELLATIONS

SLIDE_DURATION_MS = 650


class CosmicWeaverPager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.page1 = CosmicWeaverScene(PAGE_1_CONSTELLATIONS, self)
        self.page2 = CosmicWeaverScene(PAGE_2_CONSTELLATIONS, self)

        self._page1_total = self.page1.total_star_count()
        self._page2_total = self.page2.total_star_count()

        self._current_page = 1
        self._anim1 = None
        self._anim2 = None

        self._layout_pages()

    # ------------------------------------------------------------------
    def total_star_count(self):
        return self._page1_total + self._page2_total

    def current_page(self):
        """1 or 2 - which page is currently showing (or sliding toward)."""
        return self._current_page

    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        self._layout_pages()
        super().resizeEvent(event)

    def _layout_pages(self):
        """Positions both pages side by side, only one visible at a time
        (Qt naturally clips child widgets to this widget's own bounds,
        so the off-screen page simply isn't painted - no manual clip
        rect needed)."""
        w, h = self.width(), self.height()
        if self._current_page == 1:
            self.page1.setGeometry(0, 0, w, h)
            self.page2.setGeometry(w, 0, w, h)
        else:
            self.page1.setGeometry(-w, 0, w, h)
            self.page2.setGeometry(0, 0, w, h)

    # ------------------------------------------------------------------
    def set_lit_stars(self, total_count):
        """total_count: running total of lit stars across BOTH pages
        combined, clamped to the combined capacity."""
        total_count = max(0, min(total_count, self.total_star_count()))

        if total_count <= self._page1_total:
            self.page1.set_lit_stars(total_count)
            self.page2.set_lit_stars(0)
            if self._current_page != 1:
                self._slide_to(1)
        else:
            self.page1.set_lit_stars(self._page1_total)
            self.page2.set_lit_stars(total_count - self._page1_total)
            if self._current_page != 2:
                self._slide_to(2)

    def _slide_to(self, page_number):
        self._current_page = page_number
        w, h = self.width(), self.height()

        target_page1_x = 0 if page_number == 1 else -w
        target_page2_x = w if page_number == 1 else 0

        self._anim1 = QPropertyAnimation(self.page1, b"geometry", self)
        self._anim1.setDuration(SLIDE_DURATION_MS)
        self._anim1.setStartValue(self.page1.geometry())
        self._anim1.setEndValue(QRect(target_page1_x, 0, w, h))
        self._anim1.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._anim2 = QPropertyAnimation(self.page2, b"geometry", self)
        self._anim2.setDuration(SLIDE_DURATION_MS)
        self._anim2.setStartValue(self.page2.geometry())
        self._anim2.setEndValue(QRect(target_page2_x, 0, w, h))
        self._anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._anim1.start()
        self._anim2.start()


# ----------------------------------------------------------------------
# Standalone preview: `python cosmic_weaver_pager.py` - slider spans
# BOTH pages combined; drag past Page 1's total and watch it slide.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget as QW, QVBoxLayout, QSlider, QLabel
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setFixedSize(900, 600)
    central = QW()
    layout = QVBoxLayout(central)
    layout.setContentsMargins(0, 0, 0, 0)

    pager = CosmicWeaverPager()
    layout.addWidget(pager, 1)

    controls = QW()
    controls.setStyleSheet("background: #150A2E;")
    controls_layout = QVBoxLayout(controls)
    label = QLabel(f"Lit stars: 0 / {pager.total_star_count()}  (Page 1)")
    label.setStyleSheet("color: white;")
    controls_layout.addWidget(label)

    def _on_change(v):
        pager.set_lit_stars(v)
        label.setText(f"Lit stars: {v} / {pager.total_star_count()}  (Page {pager.current_page()})")

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(pager.total_star_count())
    slider.valueChanged.connect(_on_change)
    controls_layout.addWidget(slider)

    layout.addWidget(controls)
    window.setCentralWidget(central)
    window.show()
    sys.exit(app.exec())