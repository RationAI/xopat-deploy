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


def get_env_path(install_dir):
    return os.path.join(install_dir, "wsi-service", ".env")


def read_data_dir(env_path):
    """Read WS_DATA_DIR value from .env file. Returns empty string if not set."""
    if not os.path.exists(env_path):
        return ""
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("WS_DATA_DIR="):
                return line[len("WS_DATA_DIR="):].strip()
    return ""


def write_data_dir(env_path, path):
    """Write WS_DATA_DIR value into .env file, replacing the existing line."""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(env_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith("WS_DATA_DIR="):
                f.write(f"WS_DATA_DIR={path}\n")
            else:
                f.write(line)


def prompt_data_dir(env_path, first_run=False):
    """
    Open a folder picker dialog and save the chosen path to .env.
    Returns the chosen path, or None if the user cancelled.
    On first_run, cancelling exits the application.
    """
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    if first_run:
        messagebox.showinfo(
            "xOpat — Data directory",
            "Please choose the folder where your slide images are stored.\n"
            "This will be used as the root data directory for the WSI service.",
            parent=root,
        )

    chosen = filedialog.askdirectory(
        title="Select data directory for WSI service",
        parent=root,
    )
    root.destroy()

    if not chosen:
        if first_run:
            sys.exit(0)
        return None

    write_data_dir(env_path, chosen)
    return chosen


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


def stop_servers(procs):
    for p in procs:
        p.terminate()
    time.sleep(2)
    for p in procs:
        if p.poll() is None:
            p.kill()


def restart_wsi(install_dir, procs):
    """Terminate and relaunch only the wsi-service process (procs[0])."""
    p = procs[0]
    p.terminate()
    time.sleep(2)
    if p.poll() is None:
        p.kill()

    wsi_exe = os.path.join(install_dir, "wsi-service", "wsi_service_binary.exe")
    wsi_dir = os.path.join(install_dir, "wsi-service")
    procs[0] = subprocess.Popen([wsi_exe], cwd=wsi_dir, creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    install_dir = get_install_dir()
    env_path = get_env_path(install_dir)

    # First-run: prompt if WS_DATA_DIR is unset
    if not read_data_dir(env_path):
        prompt_data_dir(env_path, first_run=True)

    procs = start_servers(install_dir)

    def on_open(_icon, _):
        webbrowser.open(XOPAT_URL)

    def on_change_data_dir(_icon, _):
        def change_and_restart():
            if prompt_data_dir(env_path):
                restart_wsi(install_dir, procs)
        threading.Thread(target=change_and_restart, daemon=True).start()

    def on_stop(icon, _):
        def stop_and_exit():
            stop_servers(procs)
            icon.stop()
        threading.Thread(target=stop_and_exit, daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("Open xOpat", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Change data directory", on_change_data_dir),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stop servers", on_stop),
    )

    icon = pystray.Icon("xOpat", make_icon(), "xOpat", menu)
    icon.run()


if __name__ == "__main__":
    main()
