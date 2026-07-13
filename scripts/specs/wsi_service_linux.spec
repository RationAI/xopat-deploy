# -*- mode: python ; coding: utf-8 -*-
import os
import glob
import imagecodecs
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

block_cipher = None

# Bundle each WSI plugin's .dist-info metadata. The /alive route calls
# importlib.metadata.version("wsi_service_plugin_*"); PyInstaller bundles the
# package *source* but not its dist-info, so without this /alive 500s with
# PackageNotFoundError. Tolerant of a plugin with no metadata in the build
# env so the build never breaks on it.
def _plugin_metadata(*names):
    collected = []
    for n in names:
        try:
            collected += copy_metadata(n)
        except Exception as e:
            print(f"WARN: no dist-info metadata for {n}: {e}")
    return collected

plugin_metadata = _plugin_metadata(
    'wsi_service_plugin_openslide',
    'wsi_service_plugin_pil',
    'wsi_service_plugin_tifffile',
    'wsi_service_plugin_tiffslide',
    'wsi_service_plugin_wsidicom',
)

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
        *plugin_metadata,
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