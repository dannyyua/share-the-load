import os
import subprocess
import tempfile
import zipfile

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QToolButton, QVBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import QFile, QIODevice, QModelIndex, QTimer, Qt, QAbstractTableModel, QIdentityProxyModel, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QRestAccessManager, QNetworkRequest, QRestReply
from PySide6.QtGui import QIcon
from __feature__ import snake_case # type: ignore
from globals import version
import db_helper as db

# QComboBox but scrolling will not change selection
class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_focus_policy(Qt.StrongFocus)

        # Add clear button to deselect Splits
        self.clear_btn = QToolButton(self)
        self.clear_btn.set_icon(QIcon("circle-xmark-solid.png"))
        self.clear_btn.set_cursor(Qt.CursorShape.ArrowCursor)
        self.clear_btn.set_style_sheet("background: transparent; border: none; padding: 0px;")
        
        # Position the button on the right side
        layout = QHBoxLayout(self)
        layout.add_widget(self.clear_btn, 0, Qt.AlignmentFlag.AlignRight)
        
        # Adjust right margin so it does not block the dropdown arrow
        layout.set_contents_margins(0, 0, 20, 0) 
        
        # Connect the click event to clear selection
        self.clear_btn.clicked.connect(lambda: self.set_current_index(-1))

        self.currentIndexChanged.connect(self.update_clear_button)

    def update_clear_button(self):
        # Show the clear button only when an item is selected
        self.clear_btn.set_visible(self.current_index() != -1)

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
        self.set_window_title("Add/Edit Split")

        self.payer_splits = {}
        self.name = ""

    # Add
    def set_payers(self, payers):
        self.set_payer_splits(payers, [])

    # Edit
    def set_payer_splits(self, payers, splits):
        self.payers_dict = {p[0]: p[1] for p in payers}
        self.payer_splits = {}
        for payer in payers:
            self.payer_splits[payer[0]] = 0
        for split in splits:
            self.payer_splits[split[0]] = split[2]

    # Both Add and Edit
    def set_name(self, name):
        self.name = name

    # Populate dialog contents before showing, overloading exec()
    def exec(self):
        self.layout = QVBoxLayout()
        self.rows = []

        # Label text
        self.layout.add_widget(QLabel("Select payers and their shares:"))

        # Add a row for each payer
        for i, (id, percent) in enumerate(self.payer_splits.items()):
            row = SplitsModalRow(id, self.payers_dict[id], percent)
            self.rows.append(row)
            self.layout.add_layout(row)

        # Add a row for the split name
        name_layout = QHBoxLayout()
        name_layout.add_widget(QLabel("Split Name (optional):"))
        self.name_input = QLineEdit()
        self.name_input.set_text(self.name)
        name_layout.add_widget(self.name_input)
        self.layout.add_spacing(11)
        self.layout.add_layout(name_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.layout.add_widget(buttons)

        self.set_layout(self.layout)

        return super().exec()
        
    def get_payer_splits(self):
        return {row.get_payer_id(): row.get_percent() for row in self.rows if row.is_enabled()}
    
    def get_name(self):
        return self.name_input.text()
    
# Custom table model for SQL query results
# Only for Payers currently, may consider renaming this to reflect this
class SqlTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.refresh()
        self._headers = ["ID", "Name"]

    def row_count(self, parent=QModelIndex()):
        return len(self._data) if not parent.is_valid() else 0
    
    def column_count(self, parent=QModelIndex()):
        return len(self._headers)
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]
        return None
    
    def header_data(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def insert_row(self, name):
        self.begin_insert_rows(QModelIndex(), self.row_count(), self.row_count())
        id = db.add_payer(name)
        self._data.append((id, name))
        self.end_insert_rows()

    def update_row(self, row):
        row_index = self.match(self.index(0,0), Qt.DisplayRole, row[0])[0].row()
        db.update_payer(row[0], row[1])
        self._data[row_index] = row
        self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, self.column_count() - 1))

    def remove_row(self, id):
        row_index = self.match(self.index(0,0), Qt.DisplayRole, id)[0].row()
        self.begin_remove_rows(QModelIndex(), row_index, row_index)
        db.delete_payer(id)
        del self._data[row_index]
        self.end_remove_rows()

    def refresh(self):
        self.begin_reset_model()
        self._data = db.get_payers()
        self.end_reset_model()
    
# Special model for grouped Splits
class SplitsModel(QAbstractTableModel):
    def __init__(self, payers_model):
        super().__init__()
        self.refresh()
        self._headers = ["ID", "Distribution", "Name"]
        self._payers_model = payers_model
        self._payers_model.rowsAboutToBeRemoved.connect(self.validate_splits)

    def row_count(self, parent=QModelIndex()):
        return len(self._data) if not parent.is_valid() else 0

    def column_count(self, parent=QModelIndex()):
        return len(self._headers)
    
    def _get_payer_name_by_id(self, id):
        for row in range(self._payers_model.row_count()):
            if self._payers_model.data(self._payers_model.index(row, 0)) == id:
                return self._payers_model.data(self._payers_model.index(row, 1))

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self._data[index.row()][0] # Split ID
            elif index.column() == 1:
                return ", ".join([f"{self._get_payer_name_by_id(payer_id)} ({percent}%)" for payer_id, percent in self._data[index.row()][1]]) # Payer Name: Percent
            elif index.column() == 2:
                return self._data[index.row()][2] # Split Name
        elif role == Qt.EditRole:
            if index.column() == 0:
                return self._data[index.row()][0] # Split ID
            elif index.column() == 1:
                return [(payer_id, percent) for payer_id, percent in self._data[index.row()][1]] # List of (Payer ID, Percent)
            elif index.column() == 2:
                return self._data[index.row()][2] # Split Name
        return None

    def header_data(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def insert_row(self, payer_splits, name):
        self.begin_insert_rows(QModelIndex(), self.row_count(), self.row_count())
        id = db.add_split(payer_splits)
        db.update_split_name(id, name)
        self._data.append((id, [(payer_id, percent) for payer_id, percent in payer_splits.items()], name))
        self.end_insert_rows()

    def update_row(self, row):
        row_index = self.match(self.index(0,0), Qt.DisplayRole, row[0])[0].row()
        db.update_split(row[0], row[1])
        db.update_split_name(row[0], row[2])
        self._data[row_index] = (row[0], [(payer_id, percent) for payer_id, percent in row[1].items()], row[2])
        self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, self.column_count() - 1))
        
    def remove_row(self, id):
        row_index = self.match(self.index(0,0), Qt.DisplayRole, id)[0].row()
        self.begin_remove_rows(QModelIndex(), row_index, row_index)
        db.delete_split(id)
        del self._data[row_index]
        self.end_remove_rows()
    
    def refresh(self):
        self.begin_reset_model()

        data = db.get_splits()
        names = db.get_split_names()

        self._data = []
        split_dict = {split_id: [] for _, split_id, _ in data}
        names_dict = {split_id: name for split_id, name in names}
        for split in data:
            split_dict[split[1]].append((split[0], split[2]))
        for split_id, payer_splits in split_dict.items():
            self._data.append((split_id, payer_splits, names_dict[split_id]))

        self.end_reset_model()

    # Workaround to remove splits with deleted payers
    def validate_splits(self, parent, first, last):
        removed_payer_id = self._payers_model.data(self._payers_model.index(first, 0))

        splits_to_delete = []
        for i in range(self.row_count()):
            payer_splits_to_delete = []

            # Check for payer splits where the payer is being removed
            for j in range(len(self._data[i][1])):
                if self._data[i][1][j][0] == removed_payer_id:
                    payer_splits_to_delete.append(j)
                    
            # Delete these payer splits
            for index in payer_splits_to_delete:
                del self._data[i][1][index]

            # If split is empty, delete it too
            if len(self._data[i][1]) == 0:
                splits_to_delete.append(i)

        # Delete in reverse because we are mutating the list while iterating through it
        for index in reversed(splits_to_delete):
            self.remove_row(self._data[index][0])

# Special proxy that just changes the display text a bit for the splits dropdown
class SplitsDropdownProxy(QIdentityProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            display_text = super().data(index.sibling_at_column(2), role) or super().data(index.sibling_at_column(1), role) # Use split name if it exists, otherwise fallback to distribution
            return f"{super().data(index.sibling_at_column(0), role)}. {display_text}"
        elif role == Qt.EditRole:
            return super().data(index, role)

# Check for Updates modal
class UpdateCheckModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_modal(True)
        self.set_window_title("Check for Updates")

        self.vertical_layout = QVBoxLayout()

        self.update_text = QLabel("Checking for updates...\n\n\n")
        self.update_text.set_minimum_size(300, 300)

        # Used for tracking download URL
        self.zip_url = ""

        # Do not allow closing the window during update
        self.is_updating = False

        self.update_button = QPushButton("Update")
        self.update_button.set_enabled(False)
        self.update_button.clicked.connect(self.on_update_button_clicked)

        self.progress_bar = QProgressBar()
        self.progress_bar.set_maximum(0)
        self.progress_bar.set_text_visible(False)

        self.vertical_layout.add_widget(self.update_text)
        self.vertical_layout.add_widget(self.update_button)
        self.vertical_layout.add_widget(self.progress_bar)

        self.set_layout(self.vertical_layout)

        # Network Setup
        self.network_manager = QNetworkAccessManager(self)
        self.rest_manager = QRestAccessManager(self.network_manager, self)

        # Used so update checking isn't done too fast :)
        self.min_wait_done = False
        self.update_check_done = False

        # Update checking logic
        # Wait at least 1.5 seconds before showing update text
        QTimer.single_shot(1500, self.set_min_wait_done)

        req = QNetworkRequest(QUrl("https://api.github.com/repos/dannyyua/share-the-load/releases/latest"))
        self.reply = self.rest_manager.get(req)
        self.reply.finished.connect(self.handle_update_check_response)

    def on_update_button_clicked(self):
        selected_button = QMessageBox.warning(self, "Confirm Update", "Note: The app will restart during the update process. Please save all your work before continuing.\n\nAre you sure you want to continue?", QMessageBox.Yes | QMessageBox.No)
        if selected_button == QMessageBox.Yes:
            self.download_update(self.zip_url)

    def try_update_text(self):
        if self.min_wait_done and self.update_check_done:
            self.update_text.set_text(f"A newer version is available!\n\nCurrent version: {self.current_version}\nLatest version: {self.new_version}")
            self.update_button.set_enabled(True)
            self.progress_bar.set_maximum(100)

    def set_min_wait_done(self):
        self.min_wait_done = True
        self.try_update_text()

    def set_update_check_done(self):
        self.update_check_done = True
        self.try_update_text()

    def handle_update_check_response(self):
        rest_reply = QRestReply(self.reply)
        if rest_reply.is_success():
            json = rest_reply.read_json()[0].object()
            self.new_version = json["tag_name"]
            self.zip_url = json["assets"][0]["browser_download_url"]
            self.current_version = version

            if float(self.new_version) > float(self.current_version):
                self.set_update_check_done()
            else:
                self.update_text.set_text(f"You have the latest version.\n\nCurrent version: {self.current_version}\nLatest version: {self.new_version}")
                self.progress_bar.set_maximum(100)
        else:
            QMessageBox.critical(self, "Error", f"An error occurred while checking for updates: {self.reply.error_text()}")
            self.update_text.set_text("Update check failed.")
            self.progress_bar.set_maximum(100)

        self.reply.delete_later()

    def download_update(self, zip_url):
        self.is_updating = True
        self.update_button.set_enabled(False)
        self.progress_bar.set_maximum(0)

        self.temp_dir = tempfile.mkdtemp()
        print(self.temp_dir)
        self.zip_path = f"{self.temp_dir}\\ShareTheLoad.zip"
        self.file = QFile(self.zip_path)
        if not self.file.open(QIODevice.WriteOnly):
            QMessageBox.critical(self, "Error", f"Could not download file: {self.file.error_string()}")
            self.is_updating = False
            return

        req = QNetworkRequest(QUrl(zip_url))
        self.reply = self.network_manager.get(req)

        self.reply.readyRead.connect(self.handle_incoming_download_data)
        self.reply.finished.connect(self.handle_finished_download)

    def handle_incoming_download_data(self):
        self.file.write(self.reply.read_all())

    # Extract downloaded ZIP file and run Updater.exe
    def handle_finished_download(self):
        if self.file:
            self.file.close()

        if self.reply.error() == QNetworkReply.NoError:
            self.zip_extract_path = f"{self.temp_dir}\\ShareTheLoad"

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.zip_extract_path)

            updater_exe = os.path.join(self.zip_extract_path, "Updater.exe")

            subprocess.Popen([updater_exe, "--update-dir", os.getcwd()])

            QApplication.exit(0)
            return
        else:
            self.update_button.set_enabled(True)
            QMessageBox.critical(self, "Error", f"An error occurred during download: {self.reply.error_string()}")
            self.is_updating = False

        self.reply.delete_later()

        self.progress_bar.set_maximum(100)

    def close_event(self, event):
        if self.is_updating:
            event.ignore()
        else:
            event.accept()