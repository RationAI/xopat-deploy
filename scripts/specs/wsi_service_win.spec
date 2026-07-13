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