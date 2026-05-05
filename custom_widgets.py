from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import QModelIndex, Qt, QAbstractTableModel, QIdentityProxyModel
from __feature__ import snake_case # type: ignore

# QComboBox but scrolling will not change selection
class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_focus_policy(Qt.StrongFocus)

    def wheel_event(self, e):
        if not self.has_focus():
            e.ignore()

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
        self.percent_input.set_decimals(1)
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
    
# Custom table model for SQL query results
class SqlTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self.refresh(data)
        self._headers = headers

    def row_count(self, parent=QModelIndex()):
        return len(self._data) if not parent.is_valid() else 0
    
    def column_count(self, parent=QModelIndex()):
        return 2
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]
        return None
    
    def header_data(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def refresh(self, data):
        self.begin_reset_model()
        
        self._data = data

        self.end_reset_model()
    
# Special model for grouped Splits
class SplitsModel(QAbstractTableModel):
    def __init__(self, data, headers, payers_model):
        super().__init__()
        self.refresh(data)
        self._headers = headers
        self._payers_model = payers_model

    def row_count(self, parent=QModelIndex()):
        return len(self._data) if not parent.is_valid() else 0

    def column_count(self, parent=QModelIndex()):
        return 2
    
    def _get_payer_name_by_id(self, id):
        for row in range(self._payers_model.row_count()):
            if self._payers_model.data(self._payers_model.index(row, 0)) == id:
                return self._payers_model.data(self._payers_model.index(row, 1))

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self._data[index.row()][0] # Split ID
            else:
                return ", ".join([f"{self._get_payer_name_by_id(payer_id)}: {percent}%" for payer_id, percent in self._data[index.row()][1]]) # Payer Name: Percent
        elif role == Qt.EditRole:
            if index.column() == 0:
                return self._data[index.row()][0] # Split ID
            else:
                return [(payer_id, percent) for payer_id, percent in self._data[index.row()][1]] # List of (Payer ID, Percent)
        return None

    def header_data(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def refresh(self, data):
        self.begin_reset_model()

        self._data = []
        split_dict = {split_id: [] for _, split_id, _ in data}
        for split in data:
            split_dict[split[1]].append((split[0], split[2]))
        for split_id, payer_splits in split_dict.items():
            self._data.append((split_id, payer_splits))

        self.end_reset_model()

# Special proxy that just changes the display text a bit for the splits dropdown
class SplitsDropdownProxy(QIdentityProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return f"{super().data(index.sibling_at_column(0), role)}. {super().data(index.sibling_at_column(1), role)}"
        elif role == Qt.EditRole:
            return super().data(index.sibling_at_column(1), role)