from PySide6.QtWidgets import QComboBox
from __feature__ import snake_case # type: ignore

# QComboBox but scrolling will not change selection, and keyboard input will change selection without having to press Enter
class NoScrollComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.highlighted.connect(self.auto_select_highlighted)

    def wheel_event(self, e):
        if not self.has_focus():
            e.ignore()

    def auto_select_highlighted(self, index):
        self.set_current_index(index)