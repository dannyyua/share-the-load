# -*- mode: python ; coding: utf-8 -*-


main_a = Analysis(
    ['share_the_load_ui.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
main_pyz = PYZ(main_a.pure)

main_exe = EXE(
    main_pyz,
    main_a.scripts,
    [],
    exclude_binaries=True,
    name='ShareTheLoad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='file_version_info.txt',
    icon=['assets/icon.ico'],
    contents_directory='lib',
)

updater_a = Analysis(
    ['updater.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
updater_pyz = PYZ(updater_a.pure)

updater_exe = EXE(
    updater_pyz,
    updater_a.scripts,
    [],
    exclude_binaries=True,
    name='Updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='lib',
)

coll = COLLECT(
    main_exe,
    main_a.binaries,
    main_a.datas,
    updater_exe,
    updater_a.binaries,
    updater_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ShareTheLoad',
)
