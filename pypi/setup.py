"""Build-time hook that materializes envs/wsi_service.env into the package.

The canonical wsi_service.env lives at repo-root envs/wsi_service.env because
other (non-pypi) consumers reference it from there. The xopat package
expects it next to xopat/wsi.py at runtime; this hook copies it in before
build_py / sdist so wheels and sdists carry it via the package-data entry
declared in pyproject.toml.
"""

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "envs" / "wsi_service.env"
_DST = _HERE / "xopat" / "wsi_service.env"


def _materialize_env():
    if _SRC.exists():
        _DST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_SRC, _DST)
    elif not _DST.exists():
        raise FileNotFoundError(
            f"wsi_service.env not found at {_SRC} and no pre-copied file at "
            f"{_DST}. Build aborted: the wheel would be unusable at runtime."
        )


class build_py(_build_py):
    def run(self):
        _materialize_env()
        super().run()


class sdist(_sdist):
    def make_release_tree(self, base_dir, files):
        _materialize_env()
        super().make_release_tree(base_dir, files)


setup(cmdclass={"build_py": build_py, "sdist": sdist})
