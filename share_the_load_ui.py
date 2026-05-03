import sys

from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QGroupBox, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QTableWidget, QMainWindow, QLabel, QMenu
from PySide6.QtGui import QKeySequence
from __feature__ import snake_case

class ShareTheLoad(QMainWindow):
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

        main_menu_box = QGroupBox("Main Menu")
        payers_box = QGroupBox("Payers")
        splits_box = QGroupBox("Splits")
        payments_box = QGroupBox("View Payments")

        process_csv_layout = QVBoxLayout(main_menu_box)
        process_csv_layout.add_widget(self.upload_csv_button)
        process_csv_layout.add_widget(self.calculate_button)
        
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

        top_row_layout = QHBoxLayout()
        main_layout = QVBoxLayout()

        top_row_layout.add_widget(main_menu_box)
        top_row_layout.add_widget(payers_box)
        top_row_layout.add_widget(splits_box)
        main_layout.add_layout(top_row_layout)
        main_layout.add_widget(payments_box)
        main_layout.add_widget(self.progress_bar)

        self.set_central_widget(QWidget())
        self.central_widget().set_layout(main_layout)
        self.status_bar().add_widget(QLabel("test"))

        file_menu = QMenu("File")
        file_menu.add_action("Upload a CSV", QKeySequence.Open)
        self.menu_bar().add_menu(file_menu)

        QMessageBox.information(self, "First Launch", "Welcome to Share the Load! If this is your first time using the app, please start by adding a Payer and a Split, before processing any payments.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = ShareTheLoad()
    main_window.show()
    sys.exit(app.exec())