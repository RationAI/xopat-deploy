import platform
import urllib.request
import zipfile
import os
from pathlib import Path

GITHUB_REPO = "RationAI/xopat-deploy"
WSI_VERSION = os.environ.get("WSI_VERSION", "wsi-v1.0.0")
XOPAT_VERSION = os.environ.get("XOPAT_VERSION", "xopat-v1.0.3")
BINARIES_DIR = Path.home() / ".xopat"


def get_platform():
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Linux":
        return "linux"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    
def is_windows():
    return get_platform() == "windows"
    
def download_url(filename, tag):
    return f"https://github.com/{GITHUB_REPO}/releases/download/{tag}/{filename}"

def download_and_extract(url, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "download.zip"
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)
    zip_path.unlink()
    print("Download complete.")

def get_wsi_binary():
    plat = get_platform()
    dest = BINARIES_DIR / "wsi" / WSI_VERSION / plat
    binary_name = "wsi_service_binary.exe" if plat == "windows" else "wsi_service_binary"
    binary = dest / binary_name

    if not binary.exists():
        filename = f"wsi_service_binary_{plat}_{WSI_VERSION}.zip"
        url = download_url(filename, WSI_VERSION)
        download_and_extract(url, dest)

    if not binary.exists():
        raise FileNotFoundError(f"WSI-Service binary not found after download: {binary}")

    if plat == "linux":
        binary.chmod(0o755)

    return binary


def get_xopat_binary():
    plat = get_platform()
    dest = BINARIES_DIR / "xopat" / XOPAT_VERSION / plat
    binary_name = "xopat_binary.exe" if plat == "windows" else "xopat_binary"
    binary = dest / binary_name

    if not binary.exists():
        filename = f"xopat_{plat}_{XOPAT_VERSION}.zip"
        url = download_url(filename, XOPAT_VERSION)
        download_and_extract(url, dest)

    if not binary.exists():
        raise FileNotFoundError(f"xOpat binary not found after download: {binary}")

    if plat == "linux":
        binary.chmod(0o755)

    return binary