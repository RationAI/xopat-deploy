# -*- mode: python ; coding: utf-8 -*-
import os
import glob
import imagecodecs
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# imagecodecs: bundle .so files
imagecodecs_path = os.path.dirname(imagecodecs.__file__)
imagecodecs_sos = [(so, "imagecodecs") for so in glob.glob(os.path.join(imagecodecs_path, "*.so"))]

# OpenSlide from libs/linux/
openslide_libs = [(lib, ".") for lib in glob.glob(os.path.join("..", "..", "libs", "linux", "*.so*"))]

a = Analysis(
    ['run_wsi_service.py'],
    pathex=[],
    binaries=openslide_libs + imagecodecs_sos,
    datas=[
        ('wsi_service', 'wsi_service'),
        ('wsi_service_base_plugins', 'wsi_service_base_plugins'),
    ],
    hiddenimports=[
        *collect_submodules('wsi_service'),
        *collect_submodules('wsi_service_base_plugins'),
        'uvicorn',
        'fastapi',
        'starlette',
        'wsi_service_plugin_openslide',
        'wsi_service_plugin_pil',
        'wsi_service_plugin_tifffile',
        'wsi_service_plugin_tiffslide',
        'wsi_service_plugin_wsidicom',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[]
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='wsi_service_binary',
    debug=False,
    console=True
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='wsi_service_binary'
)