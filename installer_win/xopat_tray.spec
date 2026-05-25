# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['xopat_tray.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../assets/xopat-logo.ico', '.'),
        ('../assets/xopat-logo.png', '.'),
    ],
    hiddenimports=['pystray._win32', 'tkinter', 'tkinter.filedialog', 'tkinter.messagebox'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='xopat_tray_binary',
    debug=False,
    console=False,
    icon='../assets/xopat-logo.ico',
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='xopat_tray_binary',
)
