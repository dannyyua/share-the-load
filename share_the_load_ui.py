import sys

from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QGroupBox, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QTableWidget, QStatusBar
from __feature__ import snake_case

class ShareTheLoad(QWidget):
    def __init__(self):
        super().__init__()

        self.upload_csv_button = QPushButton("Upload a CSV")
        self.calculate_button = QPushButton("Calculate Results")
        self.payers_table = QTableWidget()
        self.payers_add_button = QPushButton("Add")
        self.payers_edit_button = QPushButton("Edit")
        self.payers_delete_button = QPushButton("Delete")
        self.splits_table = QTableWidget()
        self.splits_add_button = QPushButton("Add")
        self.splits_edit_button = QPushButton("Edit")
        self.splits_delete_button = QPushButton("Delete")
        self.payments_table = QTableWidget()

        self.progress_bar = QProgressBar()
        self.status_bar = QStatusBar()

        self.main_menu_box = QGroupBox("Main Menu")
        self.payers_box = QGroupBox("Payers")
        self.splits_box = QGroupBox("Splits")
        self.payments_box = QGroupBox("View Payments")

        self.process_csv_layout = QVBoxLayout(self.main_menu_box)
        self.process_csv_layout.add_widget(self.upload_csv_button)
        self.process_csv_layout.add_widget(self.calculate_button)
        
        self.payers_buttons_layout = QHBoxLayout()
        self.payers_buttons_layout.add_widget(self.payers_add_button)
        self.payers_buttons_layout.add_widget(self.payers_edit_button)
        self.payers_buttons_layout.add_widget(self.payers_delete_button)
        self.payers_layout = QVBoxLayout(self.payers_box)
        self.payers_layout.add_widget(self.payers_table)
        self.payers_layout.add_layout(self.payers_buttons_layout)

        self.splits_buttons_layout = QHBoxLayout()
        self.splits_buttons_layout.add_widget(self.splits_add_button)
        self.splits_buttons_layout.add_widget(self.splits_edit_button)
        self.splits_buttons_layout.add_widget(self.splits_delete_button)
        self.splits_layout = QVBoxLayout(self.splits_box)
        self.splits_layout.add_widget(self.splits_table)
        self.splits_layout.add_layout(self.splits_buttons_layout)

        self.payments_layout = QVBoxLayout(self.payments_box)
        self.payments_layout.add_widget(self.payments_table)

        self.top_row_layout = QHBoxLayout()
        self.main_layout = QVBoxLayout(self)

        self.top_row_layout.add_widget(self.main_menu_box)
        self.top_row_layout.add_widget(self.payers_box)
        self.top_row_layout.add_widget(self.splits_box)
        self.main_layout.add_layout(self.top_row_layout)
        self.main_layout.add_widget(self.payments_box)
        self.main_layout.add_widget(self.progress_bar)
        self.main_layout.add_widget(self.status_bar)

        QMessageBox.information(self, "First Launch", "Welcome to Share the Load! If this is your first time using the app, please start by adding a Payer and a Split, before processing any payments.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = ShareTheLoad()
    main_window.show()
    sys.exit(app.exec())