import filecmp
import os
import shutil
import subprocess
import sys
import argparse

from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget, QProgressBar
from PySide6.QtCore import QEventLoop, QPropertyAnimation, QTimer
from PySide6.QtGui import QFont, Qt
from __feature__ import snake_case # type: ignore
from globals import version

parser = argparse.ArgumentParser(description="Custom updater for Share the Load. For advanced use only, pass the --update-dir argument to specify where to copy update files to.")
parser.add_argument("--update-dir", type=str, required=True)
args = parser.parse_args()
update_dir = args.update_dir

# Looks pretty nice and modern with Segoe UI
font = QFont("Segoe UI", 36)

class Updater(QWidget):
    def __init__(self):
        super().__init__()

        if not update_dir:
            QApplication.exit(0)

        self.finished_updating = False

        self.set_minimum_size(600, 450)

        self.vertical_layout = QVBoxLayout(self)

        self.dot_layout = QHBoxLayout()
        self.dot_layout.set_alignment(Qt.AlignmentFlag.AlignBaseline | Qt.AlignmentFlag.AlignLeft)
        self.dot_layout.set_spacing(0)

        self.dot_index = 3

        # Update number of dots in the Updating... text
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)
        self.timer.start(1000)

        self.update_text = QLabel("Updating")
        self.update_text.set_font(font)
        self.dot_layout.add_widget(self.update_text)

        self.success_text = QLabel(f"Successfully updated Share the Load to version {version}")

        self.restart_button = QPushButton("Restart")
        self.restart_button.set_enabled(False)
        self.restart_button.clicked.connect(self.restart_app)

        self.anims = []

        for _ in range(3):
            dot = QLabel(".")
            dot.set_font(font)
            opacity_effect = QGraphicsOpacityEffect(dot)
            opacity_effect.set_opacity(0.0)
            opacity_prop = QPropertyAnimation(opacity_effect, b"opacity")
            opacity_prop.set_duration(900)
            self.anims.append(opacity_prop)
            dot.set_graphics_effect(opacity_effect)
            self.dot_layout.add_widget(dot)

        self.progress_text = QLabel("Step 1/3: Deleting existing Share the Load files...")
        self.current_file = QLabel("")
        self.progress_bar = QProgressBar()
        self.progress_bar.set_maximum(0)

        self.vertical_layout.add_stretch()
        self.vertical_layout.add_layout(self.dot_layout)
        self.vertical_layout.add_widget(self.success_text)
        self.vertical_layout.add_stretch()
        self.vertical_layout.add_widget(self.restart_button)
        self.vertical_layout.add_widget(self.progress_text)
        self.vertical_layout.add_widget(self.current_file)
        self.vertical_layout.add_widget(self.progress_bar)
        self.set_layout(self.vertical_layout)

        # Used for fading everthing out after update completes
        for obj in [self.update_text, self.success_text, self.restart_button, self.progress_text, self.current_file, self.progress_bar]: 
            opacity_effect = QGraphicsOpacityEffect(obj)
            opacity_prop = QPropertyAnimation(opacity_effect, b"opacity")
            self.anims.append(opacity_prop)
            obj.set_graphics_effect(opacity_effect)

        self.success_text.graphics_effect().set_opacity(0.0)
        self.restart_button.graphics_effect().set_opacity(0.0)

        # Initiate update
        QTimer.single_shot(1000, self.begin_update)

    # Fade in next dot until all are shown, then fade all out and repeat
    def update_dots(self):
        self.dot_index = (self.dot_index + 1) % 4

        if self.dot_index != 3:
            self.fade_in_dot(self.anims[self.dot_index])
        else:
            for i in range(3):
                self.fade_out_dot(self.anims[i])

    def fade_in_dot(self, anim):
        anim.set_start_value(0.0)
        anim.set_end_value(1.0)
        anim.start()

    def fade_out_dot(self, anim):
        anim.set_start_value(1.0)
        anim.set_end_value(0.0)
        anim.start()

    def begin_update(self):
        # Stage 1: Delete existing files

        # List of all files
        files_to_delete = [os.path.join(dirpath, f) for dirpath, _, files in os.walk(os.path.join(update_dir, "lib")) for f in files] + [os.path.join(update_dir, "ShareTheLoad.exe")]
        num_files = len(files_to_delete)
        self.progress_bar.set_maximum(num_files)

        for f in files_to_delete:
            self.current_file.set_text(f)
            self.progress_bar.set_value(self.progress_bar.value() + 1)
            os.remove(f)
            self.delay(15)

        self.delay(1000)

        # Stage 2: Copy over new files
        self.progress_bar.set_value(0)
        self.progress_text.set_text("Step 2/3: Copying new Share the Load files...")
        files_to_copy = [(dirpath, f) for dirpath, _, files in os.walk(os.getcwd()) for f in files]
        num_files = len(files_to_copy)
        self.progress_bar.set_maximum(num_files)

        for f in files_to_copy:
            self.current_file.set_text(os.path.join(f[0], f[1]))
            self.progress_bar.set_value(self.progress_bar.value() + 1)

            orig_file = os.path.join(f[0], f[1])
            dest_file = os.path.join(update_dir, os.path.relpath(orig_file, os.getcwd()))

            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            shutil.copy(orig_file, dest_file)

            self.delay(15)

        self.delay(1000)

        # Stage 3: Validate files
        self.progress_text.set_text("Step 3/3: Validating files...")
        self.progress_bar.set_maximum(0)

        for f in files_to_copy:
            self.current_file.set_text(f[1])

            orig_file = os.path.join(f[0], f[1])
            dest_file = os.path.join(update_dir, os.path.relpath(orig_file, os.getcwd()))

            if not os.path.isfile(dest_file) or not filecmp.cmp(orig_file, dest_file, shallow=False):
                QMessageBox.critical(self, "Error", f"Error: Could not validate file {dest_file}. Please retry update or manually download the new update from the Share the Load GitHub page.")
                QApplication.exit(1)
                return
            
            self.delay(15)

        self.delay(1000)

        # Stage 4: Finish update, show updated text

        # Fade out everything
        self.timer.stop()
        for anim in self.anims:
            anim.set_duration(300)
            anim.set_end_value(0.0)
            anim.start()

        self.delay(700)

        # Fade in Finished! text and Restart button
        self.update_text.set_text("Finished!")
        self.restart_button.set_enabled(True)

        for i in [3, 4, 5]:
            self.anims[i].set_start_value(0.0)
            self.anims[i].set_end_value(1.0)
            self.anims[i].start()

        self.finished_updating = True

    # May want to revise in the future
    def delay(self, milliseconds):
        delay_loop = QEventLoop()
        QTimer.single_shot(milliseconds, delay_loop.quit)
        delay_loop.exec()

    def restart_app(self):
        app_path = os.path.join(update_dir, "ShareTheLoad.exe")

        subprocess.Popen([app_path])

        QApplication.quit()

    def close_event(self, event):
        if not self.finished_updating:
            QMessageBox.warning(self, "Warning", "You cannot close the updater while it is running. Please wait for the update to finish.")
            event.ignore()
        else:
            # Trigger cleanup of update files
            pid = os.getpid()
            # Used to make sure we are in the correct directory and avoid deleting wrong files
            zip_file = os.path.join(os.path.dirname(os.getcwd()), "ShareTheLoad.zip")
            extracted_dir = os.getcwd()
            bat_file = os.path.join(os.getcwd(), "cleanup.bat")

            bat_script = f"""
                @echo off
                echo Cleaning up leftover update files...
                timeout /t 2 /nobreak >nul
                :loop
                tasklist /FI "PID eq {pid}" 2>nul | find /I "{pid}" >nul
                if %errorlevel% equ 0 (
                    timeout /t 1 /nobreak >nul
                    goto loop
                )

                if exist "{zip_file}" (
                    del /f /q "{zip_file}"
                    rmdir /s /q "{extracted_dir}"
                )
            """

            with open(bat_file, "w") as f:
                f.write(bat_script)

            subprocess.Popen(["cmd.exe", "/c", bat_file], creationflags=subprocess.CREATE_NEW_CONSOLE)

            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    updater = Updater()
    updater.show()
    sys.exit(app.exec())