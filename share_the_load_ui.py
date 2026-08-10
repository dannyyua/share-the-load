import sqlite3
import sys
import re
import configparser
import os
from datetime import datetime

from PySide6.QtWidgets import QApplication, QTableView, QWidget, QMessageBox, QGroupBox, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QTableWidget, QMainWindow, QLabel, QMenu, QFileDialog, QTableWidgetItem, QRadioButton, QInputDialog, QLineEdit, QColorDialog, QButtonGroup, QSplitter
from PySide6.QtGui import QKeySequence, QPalette, QColor, QIntValidator, QIcon
from PySide6.QtCore import QThread, Qt
from __feature__ import snake_case # type: ignore
from csv_helper import get_csv_rows
from custom_widgets import NoScrollComboBox, SplitsModal, SqlTableModel, SplitsModel, SplitsDropdownProxy, UpdateCheckModal
import db_helper as db
from enums import *

class ShareTheLoad(QMainWindow):
    def __init__(self, cursor):
        super().__init__()
        self.cursor = cursor
        self.set_window_title("Share the Load")
        self.set_window_icon(QIcon("icon.png" if os.path.isfile("icon.png") else "lib/icon.png"))

        # Models
        self.payers_model = SqlTableModel()
        self.splits_model = SplitsModel(self.payers_model)
        self.splits_dropdown_proxy = SplitsDropdownProxy()
        self.splits_dropdown_proxy.set_source_model(self.splits_model)

        # UI Elements
        self.upload_csv_button = QPushButton("Upload a CSV")
        self.calculate_button = QPushButton("Calculate Results")
        self.calculate_button.set_enabled(False)
        self.save_csv_button = QPushButton("Export CSV")
        self.save_csv_button.set_enabled(False)
        self.save_results_button = QPushButton("Export Results")
        self.save_results_button.set_enabled(False)

        self.payers_table = QTableView()
        self.payers_table.set_model(self.payers_model)
        self.payers_table.horizontal_header().set_stretch_last_section(True)
        self.payers_table.set_selection_behavior(QTableWidget.SelectRows)
        self.payers_table.vertical_header().hide()
        self.payers_add_button = QPushButton("Add")
        self.payers_edit_button = QPushButton("Edit")
        self.payers_edit_button.set_enabled(False)
        self.payers_delete_button = QPushButton("Delete")
        self.payers_delete_button.set_enabled(False)

        self.splits_table = QTableView()
        self.splits_table.set_model(self.splits_model)
        self.splits_table.horizontal_header().set_stretch_last_section(True)
        self.splits_table.set_selection_behavior(QTableWidget.SelectRows)
        self.splits_table.vertical_header().hide()
        self.splits_add_button = QPushButton("Add")
        self.splits_add_button.set_enabled(self.payers_model.row_count() > 0) # Require at least 1 payer to add splits
        self.splits_edit_button = QPushButton("Edit")
        self.splits_edit_button.set_enabled(False)
        self.splits_delete_button = QPushButton("Delete")
        self.splits_delete_button.set_enabled(False)

        self.payments_table = QTableWidget()
        self.payments_table.horizontal_header().set_stretch_last_section(True)
        self.payments_table.set_selection_behavior(QTableWidget.SelectRows)
        self.payments_auto_fit_columns_button = QPushButton("Auto-Fit Columns")
        self.payments_auto_fit_columns_button.set_enabled(False)
        self.payments_edit_mode_label = QLabel("Edit Mode:")
        self.payments_dropdown_edit = QRadioButton("Dropdown")
        self.payments_text_edit = QRadioButton("Text")
        self.payments_radio_edit = QRadioButton("Radio")
        self.payments_dropdown_edit.set_checked(True)

        self.file_selector = QFileDialog()
        self.file_selector.set_mime_type_filters(["text/csv"])

        self.file_save_results_selector = QFileDialog()
        self.file_save_results_selector.set_mime_type_filters(["text/plain"])
        self.file_save_results_selector.set_accept_mode(QFileDialog.AcceptSave)

        self.file_save_csv_selector = QFileDialog()
        self.file_save_csv_selector.set_mime_type_filters(["text/csv"])
        self.file_save_csv_selector.set_accept_mode(QFileDialog.AcceptSave)

        self.progress_bar = QProgressBar()
        self.status_text = QLabel("N/A")

        # Groups
        main_menu_box = QGroupBox("Main Menu")
        main_menu_box.set_minimum_width(200)
        payers_box = QGroupBox("Payers")
        splits_box = QGroupBox("Splits")
        payments_box = QGroupBox("Payments View")

        # Layouts
        main_menu_layout = QVBoxLayout(main_menu_box)
        main_menu_layout.add_widget(self.upload_csv_button)
        main_menu_layout.add_widget(self.calculate_button)
        main_menu_save_buttons_layout = QHBoxLayout()
        main_menu_save_buttons_layout.add_widget(self.save_csv_button)
        main_menu_save_buttons_layout.add_widget(self.save_results_button)
        main_menu_layout.add_layout(main_menu_save_buttons_layout)
        
        payers_buttons_layout = QHBoxLayout()
        payers_buttons_layout.add_widget(self.payers_add_button)
        payers_buttons_layout.add_widget(self.payers_edit_button)
        payers_buttons_layout.add_widget(self.payers_delete_button)
        payers_layout = QVBoxLayout(payers_box)
        payers_layout.add_widget(self.payers_table)
        payers_layout.add_layout(payers_buttons_layout)

        splits_buttons_layout = QHBoxLayout()
        splits_buttons_layout.add_widget(self.splits_add_button)
        splits_buttons_layout.add_widget(self.splits_edit_button)
        splits_buttons_layout.add_widget(self.splits_delete_button)
        splits_layout = QVBoxLayout(splits_box)
        splits_layout.add_widget(self.splits_table)
        splits_layout.add_layout(splits_buttons_layout)

        payments_layout = QVBoxLayout(payments_box)
        payments_layout.add_widget(self.payments_table)
        payments_edit_mode_layout = QHBoxLayout()
        payments_edit_mode_layout.add_widget(self.payments_auto_fit_columns_button)
        payments_edit_mode_layout.add_stretch()
        payments_edit_mode_layout.add_widget(self.payments_edit_mode_label)
        payments_edit_mode_layout.add_widget(self.payments_dropdown_edit)
        payments_edit_mode_layout.add_widget(self.payments_text_edit)
        payments_edit_mode_layout.add_widget(self.payments_radio_edit)
        payments_layout.add_layout(payments_edit_mode_layout)

        top_row_widget = QWidget()
        top_row_layout = QHBoxLayout(top_row_widget)
        top_row_layout.set_contents_margins(0,0,0,0) # Margins handled by QSplitter below

        # Allow vertical resizing to make payments view larger/smaller
        # Splitter doesnt support layouts so we use a widget workaround
        splitter = QSplitter()
        splitter.set_orientation(Qt.Vertical)
        splitter.set_contents_margins(11,11,11,11) # Match default layout margins
        splitter.add_widget(top_row_widget)
        splitter.add_widget(payments_box)
        splitter.add_widget(self.progress_bar)
        top_row_layout.add_widget(main_menu_box)
        top_row_layout.add_widget(payers_box)
        top_row_layout.add_widget(splits_box)

        # Inits
        self.set_central_widget(splitter)
        self.status_bar().add_widget(self.status_text)
        self.set_payments_dirty()
        self.change_color(WidgetType.CENTRAL, True)
        self.change_color(WidgetType.BUTTONS, True)
        self.edit_mode = EditMode.DROPDOWN #TODO: Save in config.ini

        file_menu = QMenu("File")
        file_menu.add_action("Upload a CSV", QKeySequence.Open)
        file_menu.add_action("Save CSV", QKeySequence.Save)
        file_menu.add_action("Save Results", QKeySequence.SaveAs)
        self.menu_bar().add_menu(file_menu)
        edit_menu = QMenu("Edit")
        edit_colors_menu = edit_menu.add_menu("Change Colors")
        edit_colors_menu.add_action("Background Color")
        edit_colors_menu.add_action("Buttons Color")
        edit_colors_menu.add_action("Reset")
        edit_menu.add_separator()
        edit_menu.add_action("Reset Data")
        self.menu_bar().add_menu(edit_menu)
        help_menu = QMenu("Help")
        help_menu.add_action("Check for Updates")
        self.menu_bar().add_menu(help_menu)

        # Tooltips
        self.upload_csv_button.set_status_tip("Open a CSV file containing payment amounts to be divided among payers.")
        self.calculate_button.set_status_tip("Calculate the amounts owed by each payer based on the splits assigned to each row in the Payments table.")
        self.save_csv_button.set_status_tip("Optional. Export the CSV file with Splits attached, for editing/viewing later.")
        self.save_results_button.set_status_tip("Optional. Export the results summary of the calculations as a TXT file.")

        # User Actions
        self.upload_csv_button.clicked.connect(self.upload_csv)
        file_menu.actions()[0].triggered.connect(self.upload_csv)
        file_menu.actions()[1].triggered.connect(self.save_csv)
        file_menu.actions()[2].triggered.connect(self.save_results)

        edit_menu.actions()[2].triggered.connect(self.reset_data)
        edit_colors_menu.actions()[0].triggered.connect(lambda: self.change_color(WidgetType.CENTRAL))
        edit_colors_menu.actions()[1].triggered.connect(lambda: self.change_color(WidgetType.BUTTONS))
        edit_colors_menu.actions()[2].triggered.connect(self.reset_colors)

        help_menu.actions()[0].triggered.connect(self.check_for_updates)

        self.calculate_button.clicked.connect(self.calculate_results)

        self.save_csv_button.clicked.connect(self.save_csv)
        self.save_results_button.clicked.connect(self.save_results)

        self.payers_add_button.clicked.connect(lambda: self.update_payer())
        self.payers_edit_button.clicked.connect(lambda: self.update_payer(True))
        self.payers_delete_button.clicked.connect(self.delete_payer)
        self.payers_table.selection_model().selectionChanged.connect(self.update_payers_buttons_state)
        self.splits_add_button.clicked.connect(lambda: self.update_split())
        self.splits_edit_button.clicked.connect(lambda: self.update_split(True))
        self.splits_delete_button.clicked.connect(self.delete_split)
        self.splits_table.selection_model().selectionChanged.connect(self.update_splits_buttons_state)
        self.payers_model.rowsInserted.connect(self.update_splits_buttons_state) # To disable adding Splits if no payers exist
        self.payers_model.rowsRemoved.connect(self.update_splits_buttons_state) # To disable adding Splits if no payers exist

        self.payments_auto_fit_columns_button.clicked.connect(self.auto_fit_columns)
        self.payments_dropdown_edit.clicked.connect(lambda: self.set_edit_mode(EditMode.DROPDOWN))
        self.payments_text_edit.clicked.connect(lambda: self.set_edit_mode(EditMode.TEXT))
        self.payments_radio_edit.clicked.connect(lambda: self.set_edit_mode(EditMode.RADIO))

        # Show welcome reminder message if no splits added yet
        if self.splits_dropdown_proxy.row_count() == 0:
            QMessageBox.information(self, "First Launch", "Welcome to Share the Load! If this is your first time using the app, please start by adding a Payer and a Split, before processing any payments.")

    def upload_csv(self):
        if (self.file_selector.exec()):
            self.set_status("Reading uploaded CSV...")

            self.upload_csv_button.set_enabled(False)
            self.calculate_button.set_enabled(False)

            self.payments_table.clear()
            self.set_payments_dirty()

            rows = get_csv_rows(self.file_selector.selected_files()[0])
            
            self.payments_table.set_row_count(len(rows)-1)

            # If CSV already has Splits column, use it, otherwise add one
            if len(rows) > 1 and rows[0][-1] == "Splits":
                self.payments_table.set_column_count(len(rows[0]))
                self.payments_table.set_horizontal_header_labels(rows[0])
            else:
                self.payments_table.set_column_count(len(rows[0]) + 1)
                self.payments_table.set_horizontal_header_labels(rows[0] + ["Splits"])

            for i in range(1, len(rows)):
                # Just for fun :)
                QThread.msleep(50)
                
                for j in range(len(rows[i])):
                    new_item = QTableWidgetItem(rows[i][j])
                    new_item.set_flags(new_item.flags() & ~Qt.ItemIsEditable)
                    self.payments_table.set_item(i-1, j, new_item)

                self.refresh_payments(i-1)
                self.set_progress(i / (len(rows)-1) * 100)

            self.upload_csv_button.set_enabled(True)
            self.calculate_button.set_enabled(True)
            self.save_csv_button.set_enabled(True)
            self.payments_auto_fit_columns_button.set_enabled(True)

            self.set_status("Successfully uploaded CSV, please edit the right-most column 'Splits' to assign splits to each row.")

    def calculate_results(self):
        if self.dirty_payments:
            self.set_status("Calculating...")

            self.results = {}

            for i in range(self.payments_table.row_count()):
                self.payments_table.select_row(i)
                self.set_progress(i / (self.payments_table.row_count()-1) * 100)

                splits_widget = self.payments_table.cell_widget(i, self.payments_table.column_count()-1)

                # Ignore row if split is empty/not selected
                if self.edit_mode == EditMode.DROPDOWN and splits_widget.current_index() == -1 or self.edit_mode == EditMode.TEXT and splits_widget.text() == "" or self.edit_mode == EditMode.RADIO and splits_widget.group.checked_id() == -1:
                    continue

                amount_indx = -1
                for j in range(self.payments_table.column_count()-1):
                    if re.match(r'^-?\d+\.?\d*$', self.payments_table.item(i, j).text()):
                        amount_indx = j
                        break

                if amount_indx == -1:
                    print(f"Warning: No transaction amount found in row {i+1}. Ignoring row.")
                    continue

                if self.edit_mode == EditMode.DROPDOWN:
                    payer_splits = self.splits_dropdown_proxy.data(self.splits_dropdown_proxy.index(splits_widget.current_index(), 1), Qt.EditRole)
                elif self.edit_mode == EditMode.TEXT:
                    payer_splits = self.get_payer_splits_by_id(int(splits_widget.text()))
                elif self.edit_mode == EditMode.RADIO:
                    payer_splits = self.get_payer_splits_by_id(int(splits_widget.group.checked_id()))

                for payer_id, percent in payer_splits:
                    if payer_id not in self.results:
                        self.results[payer_id] = 0
                    self.results[payer_id] += float(self.payments_table.item(i, amount_indx).text()) * (percent / 100)

                QThread.msleep(50)

            self.set_status("Finished calculating, displaying results...")

        # May want to separate this out into a different function
        self.dirty_payments = False
        self.save_results_button.set_enabled(True)

        selection = QMessageBox.information(self, "Calculation Results", self.get_results_summary(), QMessageBox.Ok | QMessageBox.Save)
        if selection == QMessageBox.Save:
            self.save_results()

    def get_payer_name_by_id(self, id):
        for row in range(self.payers_model.row_count()):
            if self.payers_model.data(self.payers_model.index(row, 0)) == id:
                return self.payers_model.data(self.payers_model.index(row, 1))
        return -1
    
    def get_payer_splits_by_id(self, id):
        for row in range(self.splits_model.row_count()):
            print(self.splits_model.data(self.splits_model.index(row, 1), Qt.EditRole))
            if self.splits_model.data(self.splits_model.index(row, 0)) == id:
                return self.splits_model.data(self.splits_model.index(row, 1), Qt.EditRole)
        return []
    
    # Export CSV (from Payments table)
    def save_csv(self):
        self.file_save_csv_selector.select_file(f"ShareTheLoad_payments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if self.file_save_csv_selector.exec():
            with open(self.file_save_csv_selector.selected_files()[0], "w") as f:
                # Write header
                headers = [self.payments_table.horizontal_header_item(i).text() for i in range(self.payments_table.column_count())]
                f.write(",".join(headers) + "\n")

                # Write rows
                for i in range(self.payments_table.row_count()):
                    row_data = []

                    for j in range(self.payments_table.column_count()-1):
                        item = self.payments_table.item(i, j)
                        if item is None: # Empty cell
                            item = ""
                        elif "," in item.text(): # Cell contains commas
                            item = f'"{item.text()}"' # Handle commas in amounts by wrapping in quotes
                        else:
                            item = item.text()
                        row_data.append(item)

                    # Handle splits widget based on edit mode
                    # Could refactor this
                    splits_widget = self.payments_table.cell_widget(i, self.payments_table.column_count()-1)
                    if type(splits_widget) is NoScrollComboBox and splits_widget.current_index() != -1:
                        row_data.append(str(self.splits_dropdown_proxy.data(self.splits_dropdown_proxy.index(splits_widget.current_index(), 0), Qt.EditRole)))
                    elif type(splits_widget) is QLineEdit and splits_widget.text() != "":
                        row_data.append(splits_widget.text())
                    elif type(splits_widget) is QWidget and hasattr(splits_widget, "group") and splits_widget.group.checked_id() != -1:
                        row_data.append(str(splits_widget.group.checked_id()))
                    else:
                        row_data.append("")

                    f.write(",".join(row_data) + "\n")
    
    def get_results_summary(self):
        no_results_msg = "No amounts calculated. Make sure to assign Splits under the right-most column in the Payments View."
        return f"Results:\n\n{"\n".join([f'{self.get_payer_name_by_id(id)} {'owes' if amount > 0 else 'is owed'}: ${abs(amount):.2f}' for id, amount in self.results.items()]) if self.results else no_results_msg}"

    def save_results(self):
        self.file_save_results_selector.select_file(f"ShareTheLoad_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if self.file_save_results_selector.exec():
            with open(self.file_save_results_selector.selected_files()[0], "w") as f:
                f.write(self.get_results_summary())

    def update_payer(self, edit=False):
        current_name = self.payers_table.selection_model().current_index().sibling_at_column(1).data() if edit else "" # Perhaps there is a better way to do this
        name, ok = QInputDialog.get_text(self, f"{'Edit' if edit else 'Add'} Payer", "Payer name:", QLineEdit.Normal, current_name)

        if ok and name:
            try:
                if edit: # Edit existing payer
                    id = self.payers_table.selection_model().current_index().sibling_at_column(0).data()
                    self.payers_model.update_row((id, name))
                else: # Add new payer
                    self.payers_model.insert_row(name)
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Add/Edit Payer Error", "Error: Cannot have two payers with the same name. Please try again with a unique name.")

    def delete_payer(self):
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this payer? This cannot be undone.") == QMessageBox.Yes:
            id = self.payers_table.selection_model().current_index().sibling_at_column(0).data()
            self.payers_model.remove_row(id)

    def update_split(self, edit=False):
        splits_modal = SplitsModal(self)

        # May rewrite this to eliminate dependence on DB
        payers = db.get_payers()

        if edit:
            id = self.splits_table.selection_model().current_index().sibling_at_column(0).data()

            splits = db.get_split_by_id(id)
            name = db.get_split_name_by_id(id)
            splits_modal.set_payer_splits(payers, splits)
            splits_modal.set_name(name)
        else:
            splits_modal.set_payers(payers)

        if splits_modal.exec():
            payer_splits = splits_modal.get_payer_splits()
            name = splits_modal.get_name()
            if payer_splits:
                if edit:
                    self.splits_model.update_row((id, payer_splits, name))
                else:
                    self.splits_model.insert_row(payer_splits, name)

    def delete_split(self):
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this split? This cannot be undone.") == QMessageBox.Yes:
            id = self.splits_table.selection_model().current_index().sibling_at_column(0).data()
            self.splits_model.remove_row(id)

    # Only needs to refresh Splits column
    def refresh_payments(self, row=None):
        if row is not None:
            rows = [row]
        else:
            rows = range(self.payments_table.row_count())

        for i in rows:
            current_widget = self.payments_table.cell_widget(i, self.payments_table.column_count()-1)
            current_cell = self.payments_table.item(i, self.payments_table.column_count()-1)
            current_value = None

            # Keep track of current value to retain values while switching edit modes
            if current_widget is not None:
                if type(current_widget) is NoScrollComboBox and current_widget.current_index() != -1:
                    current_value = self.splits_dropdown_proxy.data(self.splits_dropdown_proxy.index(current_widget.current_index(), 0), Qt.EditRole)
                elif type(current_widget) is QLineEdit and current_widget.text() != "":
                    current_value = current_widget.text()
                elif type(current_widget) is QWidget and hasattr(current_widget, "group") and current_widget.group.checked_id() != -1:
                    current_value = current_widget.group.checked_id()
            elif current_cell is not None and current_cell.text().isnumeric(): # Occurs when uploading CSV with Splits column already included
                current_value = current_cell.text()
                current_cell.set_text("")

            # Render either a dropdown/text input/radio buttons depending on edit mode
            if self.edit_mode == EditMode.DROPDOWN:
                splits_widget = NoScrollComboBox()
                splits_widget.set_model(self.splits_dropdown_proxy)
                splits_widget.set_current_index(-1)
                splits_widget.set_placeholder_text("No Split")

                if current_value is not None:
                    matches = self.splits_dropdown_proxy.match(self.splits_dropdown_proxy.index(0,0), Qt.EditRole, current_value)
                    if matches:
                        index = matches[0].row()
                        splits_widget.set_current_index(index)

                splits_widget.currentIndexChanged.connect(self.set_payments_dirty)
            elif self.edit_mode == EditMode.TEXT:
                splits_widget = QLineEdit()
                splits_widget.set_placeholder_text("Enter a Split ID or leave empty to ignore...")
                splits_widget.set_validator(QIntValidator(0, 2147483647))

                if current_value is not None:
                    splits_widget.set_text(str(current_value))

                splits_widget.returnPressed.connect(self.select_next_payments_row)

                splits_widget.textChanged.connect(self.set_payments_dirty)
            elif self.edit_mode == EditMode.RADIO:
                splits_widget = QWidget()
                splits_widget_layout = QHBoxLayout(splits_widget)

                splits_widget_group = QButtonGroup(splits_widget)
                splits_widget.group = splits_widget_group # Reference to group from base widget
                for k in range(self.splits_model.row_count()):
                    split_id = self.splits_model.data(self.splits_model.index(k, 0))
                    split_radio = QRadioButton(str(split_id))
                    splits_widget_group.add_button(split_radio, split_id)
                    splits_widget_layout.add_widget(split_radio)

                if current_value is not None:
                    splits_widget_group.button(int(current_value)).set_checked(True)
                
                splits_widget_group.buttonClicked.connect(self.set_payments_dirty)

            self.payments_table.set_cell_widget(i, self.payments_table.column_count()-1, splits_widget)

    # QOL feature to allow fast input when in text edit mode by moving to next row after pressing Enter
    def select_next_payments_row(self):
        current_row = self.payments_table.current_row()
        if current_row < self.payments_table.row_count() - 1:
            self.payments_table.set_current_index(self.payments_table.model().index(current_row + 1, self.payments_table.current_column()))

    def update_payers_buttons_state(self):
        has_selected = len(self.payers_table.selection_model().selected_rows()) != 0

        self.payers_edit_button.set_enabled(has_selected)
        self.payers_delete_button.set_enabled(has_selected)

    def update_splits_buttons_state(self):
        has_selected = len(self.splits_table.selection_model().selected_rows()) != 0
        has_valid_payers = self.payers_model.row_count() > 0

        self.splits_add_button.set_enabled(has_valid_payers)
        self.splits_edit_button.set_enabled(has_selected)
        self.splits_delete_button.set_enabled(has_selected)

    def set_status(self, new_status):
        self.status_text.set_text(new_status)

    def set_progress(self, value):
        if value == 0:
            self.progress_bar.reset()
        else:
            self.progress_bar.set_value(value)

    def set_payments_dirty(self):
        self.dirty_payments = True
        self.save_results_button.set_enabled(False)

    def auto_fit_columns(self):
        # Auto fit all columns other than Splits column
        for i in range(self.payments_table.column_count()-1):
            self.payments_table.resize_column_to_contents(i)

    def reset_data(self):
        if QMessageBox.question(self, "Confirm Reset", "Are you sure you want to reset all data? This cannot be undone.") == QMessageBox.Yes:
            db.reset_data()
            self.payers_model.refresh()
            self.splits_model.refresh()

    # Just for fun :)
    def change_color(self, widget_type, init=False):
        config = configparser.ConfigParser()
        config.read("config.ini")

        if init: # Set colors if colors are in config, otherwise ignore
            if config.has_option("Colors", widget_type.name):
                selected_color = QColor(config["Colors"][widget_type.name])
            else:
                return
        else: # Prompt user for new color, using default from config if it exists
            if config.has_option("Colors", widget_type.name):
                selected_color = QColorDialog.get_color(QColor(config["Colors"][widget_type.name]))
            else:
                selected_color = QColorDialog.get_color()

        if selected_color.is_valid():
            if widget_type == WidgetType.CENTRAL: # Window Background
                palette = self.palette()
                palette.set_color(QPalette.Window, selected_color)
                self.set_palette(palette)
            elif widget_type == WidgetType.BUTTONS: # Buttons Only
                # Workaround because palette doesn't seem to work on push buttons
                self.central_widget().set_style_sheet(f"QPushButton {{ background-color: {selected_color.name()}; }}")

            if not config.has_section("Colors"):
                config.add_section("Colors")
            config["Colors"][widget_type.name] = selected_color.name()

            with open("config.ini", "w") as config_file:
                config.write(config_file)

    # Reset palette, style sheet, and config
    # May need to update if config is used for other stuff
    def reset_colors(self):
        self.set_palette(QPalette())
        self.central_widget().set_style_sheet("")

        with open("config.ini", "w") as config_file:
            config_file.write("")
            
    def set_edit_mode(self, edit_mode):
        self.edit_mode = edit_mode
        self.refresh_payments()

    def check_for_updates(self):
        update_modal = UpdateCheckModal(self)
        update_modal.exec()
            
if __name__ == "__main__":
    cursor = db.start_db()

    app = QApplication(sys.argv)
    main_window = ShareTheLoad(cursor)
    main_window.show()
    sys.exit(app.exec())