import sys
import re
import configparser

from PySide6.QtWidgets import QApplication, QTableView, QWidget, QMessageBox, QGroupBox, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QTableWidget, QMainWindow, QLabel, QMenu, QFileDialog, QTableWidgetItem, QRadioButton, QInputDialog, QLineEdit, QColorDialog
from PySide6.QtGui import QKeySequence, QPalette, QColor
from PySide6.QtCore import QThread, Qt
from __feature__ import snake_case # type: ignore
from csv_helper import get_csv_rows
from custom_widgets import NoScrollComboBox, SplitsModal, SqlTableModel, SplitsModel, SplitsDropdownProxy
import db_helper as db
from enum import Enum

class WidgetType(Enum):
    CENTRAL = 0,
    BUTTONS = 1

class ShareTheLoad(QMainWindow):
    def __init__(self, cursor):
        super().__init__()
        self.cursor = cursor

        # Models
        self.payers_model = SqlTableModel(db.get_payers(), ["ID", "Name"])
        self.splits_model = SplitsModel(db.get_splits(), ["ID", "Distribution"], self.payers_model)
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
        self.splits_edit_button = QPushButton("Edit")
        self.splits_edit_button.set_enabled(False)
        self.splits_delete_button = QPushButton("Delete")
        self.splits_delete_button.set_enabled(False)

        self.payments_table = QTableWidget()
        self.payments_table.horizontal_header().set_stretch_last_section(True)
        self.payments_auto_fit_columns_button = QPushButton("Auto-Fit Columns")
        self.payments_auto_fit_columns_button.set_enabled(False)
        self.payments_edit_mode_label = QLabel("Edit Mode:")
        self.payments_dropdown_edit = QRadioButton("Dropdown")
        self.payments_text_edit = QRadioButton("Text")
        self.payments_text_edit.set_enabled(False)
        self.payments_dropdown_edit.set_checked(True)

        self.file_selector = QFileDialog()
        self.file_selector.set_mime_type_filters(["text/csv"])

        self.file_save_selector = QFileDialog()
        self.file_save_selector.set_mime_type_filters(["text/plain"])

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
        payments_layout.add_layout(payments_edit_mode_layout)

        top_row_layout = QHBoxLayout()
        main_layout = QVBoxLayout()

        top_row_layout.add_widget(main_menu_box)
        top_row_layout.add_widget(payers_box)
        top_row_layout.add_widget(splits_box)
        main_layout.add_layout(top_row_layout)
        main_layout.add_widget(payments_box)
        main_layout.add_widget(self.progress_bar)

        # Inits
        self.set_central_widget(QWidget())
        self.central_widget().set_layout(main_layout)
        self.status_bar().add_widget(self.status_text)
        self.set_payments_dirty()
        self.change_color(WidgetType.CENTRAL, True)
        self.change_color(WidgetType.BUTTONS, True)

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

        # Tooltips
        self.upload_csv_button.set_status_tip("Open a CSV file containing payment amounts to be divided among payers.")
        self.calculate_button.set_status_tip("Calculate the amounts owed by each payer based on the splits assigned to each row in the Payments table.")
        self.save_csv_button.set_status_tip("Optional. Export the CSV file with Splits attached, for editing/viewing later.")
        self.save_results_button.set_status_tip("Optional. Export the results summary of the calculations as a TXT file.")

        # User Actions
        self.upload_csv_button.clicked.connect(self.upload_csv)
        file_menu.actions()[0].triggered.connect(self.upload_csv)

        edit_menu.actions()[2].triggered.connect(self.reset_data)
        edit_colors_menu.actions()[0].triggered.connect(lambda: self.change_color(WidgetType.CENTRAL))
        edit_colors_menu.actions()[1].triggered.connect(lambda: self.change_color(WidgetType.BUTTONS))
        edit_colors_menu.actions()[2].triggered.connect(self.reset_colors)

        self.calculate_button.clicked.connect(self.calculate_results)

        self.save_results_button.clicked.connect(self.save_results)

        self.payers_add_button.clicked.connect(lambda: self.update_payer())
        self.payers_edit_button.clicked.connect(lambda: self.update_payer(True))
        self.payers_delete_button.clicked.connect(self.delete_payer)
        self.payers_table.selection_model().selectionChanged.connect(self.update_payers_buttons_state)
        self.splits_add_button.clicked.connect(lambda: self.update_split())
        self.splits_edit_button.clicked.connect(lambda: self.update_split(True))
        self.splits_delete_button.clicked.connect(self.delete_split)
        self.splits_table.selection_model().selectionChanged.connect(self.update_splits_buttons_state)

        self.payments_auto_fit_columns_button.clicked.connect(self.auto_fit_columns)

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
            self.payments_table.set_column_count(len(rows[0]) + 1)

            self.payments_table.set_horizontal_header_labels(rows[0] + ["Splits"])

            for i in range(1, len(rows)):
                # Just for fun :)
                QThread.msleep(50)
                
                for j in range(len(rows[i])):
                    new_item = QTableWidgetItem(rows[i][j])
                    new_item.set_flags(new_item.flags() & ~Qt.ItemIsEditable)
                    self.payments_table.set_item(i-1, j, new_item)
                splits_dropdown = NoScrollComboBox()
                splits_dropdown.set_model(self.splits_dropdown_proxy)
                splits_dropdown.set_current_index(-1)
                splits_dropdown.set_placeholder_text("No Split")
                splits_dropdown.currentIndexChanged.connect(self.set_payments_dirty)
                self.payments_table.set_cell_widget(i-1, len(rows[i]), splits_dropdown)

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

                if self.payments_table.cell_widget(i, self.payments_table.column_count()-1).current_index() == -1:
                    continue

                amount_indx = -1
                for j in range(self.payments_table.column_count()-1):
                    if re.match(r'^-?\d+\.?\d*$', self.payments_table.item(i, j).text()):
                        amount_indx = j
                        break

                if amount_indx == -1:
                    print(f"Warning: No transaction amount found in row {i+1}. Ignoring row.")
                    continue

                payer_splits = self.splits_dropdown_proxy.data(self.splits_dropdown_proxy.index(self.payments_table.cell_widget(i, self.payments_table.column_count()-1).current_index(), 0), Qt.EditRole)
                for payer_id, percent in payer_splits:
                    if payer_id not in self.results:
                        self.results[payer_id] = 0
                    self.results[payer_id] += float(self.payments_table.item(i, amount_indx).text()) * (percent / 100)

                QThread.msleep(50)

            self.set_status("Finished calculating, displaying results...")

        self.dirty_payments = False
        self.save_results_button.set_enabled(True)
        QMessageBox.information(self, "Calculation Results", f"Results:\n\n{"\n".join([f'{self.get_payer_name_by_id(id)} {'owes' if amount > 0 else 'is owed'}: ${abs(amount):.2f}' for id, amount in self.results.items()]) if self.results else "No amounts calculated. Make sure to assign Splits under the right-most column in the Payments View."}")

    def get_payer_name_by_id(self, id):
        for row in range(self.payers_model.row_count()):
            if self.payers_model.data(self.payers_model.index(row, 0)) == id:
                return self.payers_model.data(self.payers_model.index(row, 1))

    def save_results(self):
        if self.file_save_selector.exec():
            # with open(self.file_save_selector.selected_files()[0], "w") as f:
            #     f.write("TBD")
            pass

    def refresh_payers(self):
        payers = db.get_payers()
        self.payers_model.refresh(payers)

    def update_payer(self, edit=False):
        current_name = self.payers_table.selection_model().current_index().sibling_at_column(1).data() if edit else "" # Perhaps there is a better way to do this
        name, ok = QInputDialog.get_text(self, f"{'Edit' if edit else 'Add'} Payer", "Payer name:", QLineEdit.Normal, current_name)

        if ok and name:
            if edit: # Edit existing payer
                id = self.payers_table.selection_model().current_index().sibling_at_column(0).data()
                db.update_payer(id, name)
            else: # Add new payer
                db.add_payer(name)

        self.refresh_tables()

    def delete_payer(self):
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this payer? This cannot be undone.") == QMessageBox.Yes:
            id = self.payers_table.selection_model().current_index().sibling_at_column(0).data()
            db.delete_payer(id)
            self.refresh_tables()

    def refresh_splits(self):
        splits = db.get_splits()
        self.splits_model.refresh(splits)

    def update_split(self, edit=False):
        splits_modal = SplitsModal(self)

        payers = db.get_payers()

        if edit:
            id = self.splits_table.selection_model().current_index().sibling_at_column(0).data()

            splits = db.get_split_by_id(id)
            splits_modal.set_payer_splits(payers, splits)
        else:
            splits_modal.set_payers(payers)

        if splits_modal.exec():
            payer_splits = splits_modal.get_payer_splits()
            if payer_splits:
                if edit:
                    db.update_split(id, payer_splits)
                else:
                    db.add_split(payer_splits)

                self.refresh_splits()
                self.refresh_payments()

    def delete_split(self):
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this split? This cannot be undone.") == QMessageBox.Yes:
            id = self.splits_table.selection_model().current_index().sibling_at_column(0).data()
            db.delete_split(id)
            self.refresh_splits()

    # Only needs to refresh Splits column
    def refresh_payments(self):
        pass
        # for i in range(self.payments_table.row_count()):


    def refresh_tables(self):
        self.refresh_payers()
        self.refresh_splits()
        self.refresh_payments()

    def update_payers_buttons_state(self):
        has_selected = len(self.payers_table.selection_model().selected_rows()) != 0

        self.payers_edit_button.set_enabled(has_selected)
        self.payers_delete_button.set_enabled(has_selected)

    def update_splits_buttons_state(self):
        has_selected = len(self.splits_table.selection_model().selected_rows()) != 0

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
        self.payments_table.resize_columns_to_contents()

    def reset_data(self):
        if QMessageBox.question(self, "Confirm Reset", "Are you sure you want to reset all data? This cannot be undone.") == QMessageBox.Yes:
            db.reset_data()
            self.refresh_tables()

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
            
            
if __name__ == "__main__":
    cursor = db.start_db()

    app = QApplication(sys.argv)
    main_window = ShareTheLoad(cursor)
    main_window.show()
    sys.exit(app.exec())