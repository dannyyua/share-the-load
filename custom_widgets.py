from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from __feature__ import snake_case # type: ignore

# QComboBox but scrolling will not change selection, and keyboard input will change selection without having to press Enter
class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighted.connect(self.auto_select_highlighted)
        self.set_focus_policy(Qt.StrongFocus)

    def wheel_event(self, e):
        if not self.has_focus():
            e.ignore()

    def auto_select_highlighted(self, index):
        self.set_current_index(index)

class SplitsModalRow(QHBoxLayout):
    def __init__(self, id, payer_name, percent):
        super().__init__()
        self.id = id
        self.payer_name = payer_name
        self.checkbox = QCheckBox(payer_name)
        self.checkbox.set_checked(percent > 0)
        
        self.percent_input = QDoubleSpinBox()
        self.percent_input.set_value(percent)
        self.percent_input.set_suffix("%")
        self.percent_input.set_range(0, 100)
        self.percent_input.set_enabled(self.checkbox.is_checked())

        self.checkbox.checkStateChanged.connect(lambda: self.percent_input.set_enabled(self.checkbox.is_checked()))

        self.add_widget(self.checkbox)
        self.add_widget(self.percent_input)

    def get_payer_id(self):
        return self.id

    def get_payer_name(self):
        return self.payer_name
    
    def get_percent(self):
        return self.percent_input.value()

    def is_enabled(self):
        return self.checkbox.is_checked() and self.get_percent() > 0

# Customised QDialog for assigning payers to splits
class SplitsModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_modal(True)

    # Add
    def set_payers(self, payers):
        self.set_payer_splits(payers, [])

    # Edit
    def set_payer_splits(self, payers, splits):
        self.payer_splits = {}
        for payer in payers:
            self.payer_splits[payer[0]] = 0
        for split in splits:
            self.payer_splits[split[0]] = split[2]

        payers_dict = {p[0]: p[1] for p in payers}

        self.layout = QVBoxLayout()
        self.rows = []
        for i, (id, percent) in enumerate(self.payer_splits.items()):
            row = SplitsModalRow(id, payers_dict[id], percent)
            self.rows.append(row)
            self.layout.add_layout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.layout.add_widget(buttons)

        self.set_layout(self.layout)
        
    def get_payer_splits(self):
        return {row.get_payer_id(): row.get_percent() for row in self.rows if row.is_enabled()}