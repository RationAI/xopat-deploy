import os
import sys
import time
import threading
import webbrowser
import subprocess
import ctypes

import pystray
from PIL import Image, ImageDraw

XOPAT_URL = "http://localhost:9000/"


def get_install_dir():
    """Return the xOpat installation root (parent of this exe's directory)."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle inside xopat_tray_binary/
        return os.path.dirname(os.path.dirname(sys.executable))
    # Running as plain script from installer_win/
    return os.path.dirname(os.path.abspath(__file__))


def make_icon():
    """Generate a simple teal circle icon for the system tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill=(0, 140, 186))
    d.ellipse([20, 20, size - 20, size - 20], fill=(255, 255, 255))
    return img


def start_servers(install_dir):
    env = os.environ.copy()
    env["XOPAT_CACHE_DIR"] = os.path.join(install_dir, "xopat", "cache")

    wsi_exe = os.path.join(install_dir, "wsi-service", "wsi_service_binary.exe")
    xopat_exe = os.path.join(install_dir, "xopat", "xopat_binary.exe")
    wsi_dir = os.path.join(install_dir, "wsi-service")

    no_window = subprocess.CREATE_NO_WINDOW
    procs = [subprocess.Popen([wsi_exe], cwd=wsi_dir, env=env, creationflags=no_window)]
    time.sleep(3)
    procs.append(subprocess.Popen([xopat_exe], env=env, creationflags=no_window))
    time.sleep(2)
    webbrowser.open(XOPAT_URL)
    return procs


def stop_servers(procs, icon):
    def _do():
        for p in procs:
            p.terminate()
        time.sleep(2)
        for p in procs:
            if p.poll() is None:
                p.kill()
        icon.stop()

    threading.Thread(target=_do, daemon=True).start()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    install_dir = get_install_dir()
    procs = start_servers(install_dir)

    icon_holder = [None]

    def on_open(icon, _):
        webbrowser.open(XOPAT_URL)

    def on_stop(icon, _):
        stop_servers(procs, icon)

    menu = pystray.Menu(
        pystray.MenuItem("Open xOpat", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stop servers", on_stop),
    )

    icon = pystray.Icon("xOpat", make_icon(), "xOpat", menu)
    icon_holder[0] = icon
    icon.run()


if __name__ == "__main__":
    main()
