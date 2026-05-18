import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox

import pystray
from PIL import Image

XOPAT_PORT = 9001
WSI_PORT = 8050
XOPAT_URL = f"http://localhost:{XOPAT_PORT}/"


def get_install_dir():
    """Return the xOpat installation root directory."""
    return os.path.dirname(os.path.dirname(sys.executable))


def get_env_path(install_dir):
    """Return path to the wsi-service .env file."""
    return os.path.join(install_dir, "wsi-service", ".env")


def read_data_dir(env_path):
    """Read WS_DATA_DIR from .env file, or return empty string if not set."""
    if not os.path.exists(env_path):
        return ""
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("WS_DATA_DIR="):
                return line[len("WS_DATA_DIR="):].strip()
    return ""


def write_data_dir(env_path, path):
    """Update WS_DATA_DIR in .env file."""
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
    """Show a folder picker and save the chosen path to .env. On first_run, cancelling exits the app."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    if first_run:
        messagebox.showinfo(
            "xOpat",
            "Please select the folder with your slides.\n"
            "You can always change this later.",
            parent=root,
        )

    chosen = filedialog.askdirectory(
        title="xOpat — Select slides folder",
        parent=root,
    )
    root.destroy()

    if not chosen:
        if first_run:
            sys.exit(0)
        return None

    write_data_dir(env_path, chosen)
    return chosen


def load_tray_icon():
    """Load the xOpat logo for the system tray."""
    base = os.path.join(os.path.dirname(sys.executable), "_internal")
    return Image.open(os.path.join(base, "xopat-logo.png"))


def start_servers(install_dir):
    """Launch wsi-service and xOpat, then open the browser."""
    env = os.environ.copy()
    env["WSI_PORT"] = str(WSI_PORT)
    env["XOPAT_NODE_PORT"] = str(XOPAT_PORT)
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
    """Terminate all server processes."""
    for p in procs:
        p.terminate()
    time.sleep(2)
    for p in procs:
        if p.poll() is None:
            p.kill()


def restart_wsi(install_dir, procs):
    """Restart only the wsi-service process."""
    p = procs[0]
    p.terminate()
    time.sleep(2)
    if p.poll() is None:
        p.kill()

    wsi_exe = os.path.join(install_dir, "wsi-service", "wsi_service_binary.exe")
    wsi_dir = os.path.join(install_dir, "wsi-service")
    procs[0] = subprocess.Popen([wsi_exe], cwd=wsi_dir, creationflags=subprocess.CREATE_NO_WINDOW)


def set_dpi_awareness():
    """Ensure sharp rendering on high-resolution screens."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def is_port_in_use(port):
    """Return True if something is already listening on the given port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def on_open(icon, item):
    """Open xOpat in the default browser."""
    webbrowser.open(XOPAT_URL)


def stop_and_exit(procs, icon):
    """Stop all servers and close the tray icon."""
    stop_servers(procs)
    icon.stop()


def change_and_restart(env_path, install_dir, procs):
    """Prompt for a new slides folder and restart wsi-service."""
    if prompt_data_dir(env_path):
        restart_wsi(install_dir, procs)


def main():
    """Start servers and show the system tray."""
    if is_port_in_use(XOPAT_PORT):
        webbrowser.open(XOPAT_URL)
        return

    set_dpi_awareness()

    install_dir = get_install_dir()
    env_path = get_env_path(install_dir)

    # First-run: prompt if WS_DATA_DIR is unset
    if not read_data_dir(env_path):
        prompt_data_dir(env_path, first_run=True)

    procs = start_servers(install_dir)

    # Defined here to capture procs, env_path, install_dir from this scope
    def on_stop(icon, item):
        threading.Thread(target=stop_and_exit, args=(procs, icon), daemon=True).start()

    def on_change_data_dir(icon, item):
        threading.Thread(target=change_and_restart, args=(env_path, install_dir, procs), daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("Open xOpat", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Change slides folder", on_change_data_dir),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_stop),
    )

    icon = pystray.Icon("xOpat", load_tray_icon(), "xOpat", menu)
    icon.run()


if __name__ == "__main__":
    main()
