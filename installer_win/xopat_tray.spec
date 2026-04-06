# -*- mode: python ; coding: utf-8 -*-
# Build from the installer_win/ directory:
#   pip install pystray Pillow pyinstaller
#   pyinstaller xopat_tray.spec
# Output lands in dist/xopat_tray_binary/ — copy that folder into
# installer_win/packages/xopat/data/ before building the Qt IFW installer.

a = Analysis(
    ['xopat_tray.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pystray._win32'],
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
