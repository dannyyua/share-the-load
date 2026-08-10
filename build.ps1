# python3 -m PyInstaller --noconsole --name "ShareTheLoad" --icon icon.ico --contents-directory lib --add-data "icon.png:." --version-file file_version_info.txt share_the_load_ui.py
# python3 -m PyInstaller --noconsole --name "Updater" --contents-directory lib updater.py

python3 -m PyInstaller build.spec