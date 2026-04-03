import subprocess
import os
import signal
import time
import urllib.request
import os
from pathlib import Path
from .download import is_windows

class XOpat:
    def __init__(self, proc, base_url):
        self.proc = proc
        self.base_url = base_url

    def stop(self):
        print("Stopping xOpat...")
        try:
            if is_windows():
                self.proc.terminate()
            else:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            except Exception:
                pass
            self.proc.wait()
        print("xOpat stopped.")

def start_xopat(binary):
    binary = Path(binary)
    env = os.environ.copy()
    env["XOPAT_CACHE_DIR"] = str(binary.parent / "cache")

    print("Starting xOpat...")
    if is_windows():
        proc = subprocess.Popen(
            [str(binary)],
            cwd=str(binary.parent),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            [str(binary)],
            cwd=str(binary.parent),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )

    prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "").rstrip("/")
    base_url = f"{prefix}/proxy/9000" if prefix else "http://127.0.0.1:9000"

    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:9000", timeout=0.5)
            print("xOpat is running.")
            return XOpat(proc, base_url)
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("xOpat did not start on http://127.0.0.1:9000")