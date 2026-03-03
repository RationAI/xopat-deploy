# -*- mode: python ; coding: utf-8 -*-
import os
import glob
import imagecodecs
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# imagecodecs: bundle .pyd + .dll
imagecodecs_path = os.path.dirname(imagecodecs.__file__)
imagecodecs_bins = []
imagecodecs_bins += [(p, "imagecodecs") for p in glob.glob(os.path.join(imagecodecs_path, "*.pyd"))]
imagecodecs_bins += [(d, "imagecodecs") for d in glob.glob(os.path.join(imagecodecs_path, "*.dll"))]

# OpenSlide DLLs from repo root: libs/windows/*.dll (spec runs inside external/wsi-service)
openslide_dlls = [(dll, ".") for dll in glob.glob(os.path.join("..", "..", "libs", "windows", "*.dll"))]

a = Analysis(
    ['run_wsi_service.py'],
    pathex=[],
    binaries=openslide_dlls + imagecodecs_bins,
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